#!/usr/bin/env python3
"""Blink SOS on the Raspberry Pi ACT LED while internet is unavailable."""

from __future__ import annotations

import argparse
import os
import signal
import socket
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_PROBES = ("1.1.1.1:443", "8.8.8.8:53")
DEFAULT_LED_CANDIDATES = (
    Path("/sys/class/leds/led0"),
    Path("/sys/class/leds/ACT"),
    Path("/sys/class/leds/act"),
)
MORSE_SOS = (".", ".", ".", "-", "-", "-", ".", ".", ".")


class StopRequested(Exception):
    """Raised when systemd or an operator asks the watchdog to stop."""


@dataclass(frozen=True)
class ProbeTarget:
    host: str
    port: int


@dataclass
class LedState:
    trigger: str | None
    brightness: str | None


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None


def write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")


def selected_trigger(raw_trigger: str | None) -> str | None:
    if not raw_trigger:
        return None

    for token in raw_trigger.split():
        if token.startswith("[") and token.endswith("]"):
            return token[1:-1]
    return None


class ActivityLed:
    def __init__(self, led_dir: Path) -> None:
        self.led_dir = led_dir
        self.trigger_path = led_dir / "trigger"
        self.brightness_path = led_dir / "brightness"
        self._saved_state: LedState | None = None

    def save(self) -> None:
        if self._saved_state is None:
            self._saved_state = LedState(
                trigger=selected_trigger(read_text(self.trigger_path)),
                brightness=read_text(self.brightness_path),
            )

    def set_manual(self) -> None:
        self.save()
        if self.trigger_path.exists():
            write_text(self.trigger_path, "none")

    def set_brightness(self, enabled: bool) -> None:
        write_text(self.brightness_path, "1" if enabled else "0")

    def pulse(self, on_seconds: float, deadline: float) -> None:
        if time.monotonic() >= deadline:
            return

        self.set_brightness(True)
        interruptible_sleep(min(on_seconds, max(0.0, deadline - time.monotonic())))
        self.set_brightness(False)

    def sos_for(self, duration_seconds: float, unit_seconds: float) -> None:
        self.set_manual()
        deadline = time.monotonic() + duration_seconds
        while time.monotonic() < deadline:
            self.sos_once(unit_seconds, deadline)

    def sos_once(self, unit_seconds: float, deadline: float | None = None) -> None:
        self.set_manual()
        for index, symbol in enumerate(MORSE_SOS):
            if deadline is not None and time.monotonic() >= deadline:
                return

            self.pulse(unit_seconds if symbol == "." else unit_seconds * 3, deadline or float("inf"))

            if index == len(MORSE_SOS) - 1:
                gap = unit_seconds * 7
            elif index in (2, 5):
                gap = unit_seconds * 3
            else:
                gap = unit_seconds

            if deadline is None:
                interruptible_sleep(gap)
            else:
                interruptible_sleep(min(gap, max(0.0, deadline - time.monotonic())))

    def restore(self) -> None:
        if self._saved_state is None:
            return

        state = self._saved_state
        try:
            if state.trigger:
                write_text(self.trigger_path, state.trigger)
            if state.brightness is not None:
                write_text(self.brightness_path, state.brightness)
        finally:
            self._saved_state = None


def interruptible_sleep(seconds: float) -> None:
    if seconds <= 0:
        return
    time.sleep(seconds)


def parse_probe(value: str) -> ProbeTarget:
    host, separator, port_text = value.rpartition(":")
    if not separator or not host:
        raise argparse.ArgumentTypeError(f"probe must use host:port format: {value!r}")

    try:
        port = int(port_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"probe port must be an integer: {value!r}") from exc

    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"probe port is out of range: {value!r}")
    return ProbeTarget(host=host, port=port)


def env_list(name: str, default: Iterable[str]) -> list[str]:
    raw_value = os.environ.get(name)
    if not raw_value:
        return list(default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def resolve_led_dir(configured: str | None) -> Path:
    if configured:
        led_dir = Path(configured)
        if led_dir.exists():
            return led_dir
        raise FileNotFoundError(f"configured LED path does not exist: {led_dir}")

    for candidate in DEFAULT_LED_CANDIDATES:
        if candidate.exists():
            return candidate

    names = ", ".join(str(path) for path in DEFAULT_LED_CANDIDATES)
    raise FileNotFoundError(f"could not find Raspberry Pi ACT LED; checked {names}")


def internet_is_reachable(probes: Iterable[ProbeTarget], timeout_seconds: float) -> bool:
    for probe in probes:
        try:
            with socket.create_connection((probe.host, probe.port), timeout=timeout_seconds):
                return True
        except OSError:
            continue
    return False


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Blink SOS on the Raspberry Pi green ACT LED while internet access is down."
    )
    parser.add_argument(
        "--led",
        default=os.environ.get("INTERNET_WATCHDOG_LED"),
        help="LED sysfs directory, for example /sys/class/leds/led0",
    )
    parser.add_argument(
        "--probe",
        action="append",
        type=parse_probe,
        default=None,
        help="Connectivity probe in host:port format. May be repeated.",
    )
    parser.add_argument(
        "--interval",
        type=positive_float,
        default=float(os.environ.get("INTERNET_WATCHDOG_INTERVAL_SECONDS", "10")),
        help="Seconds between connectivity checks.",
    )
    parser.add_argument(
        "--timeout",
        type=positive_float,
        default=float(os.environ.get("INTERNET_WATCHDOG_TIMEOUT_SECONDS", "3")),
        help="TCP timeout for each probe.",
    )
    parser.add_argument(
        "--fail-threshold",
        type=positive_int,
        default=int(os.environ.get("INTERNET_WATCHDOG_FAIL_THRESHOLD", "3")),
        help="Consecutive failed checks required before blinking starts.",
    )
    parser.add_argument(
        "--morse-unit",
        type=positive_float,
        default=float(os.environ.get("INTERNET_WATCHDOG_MORSE_UNIT_SECONDS", "0.2")),
        help="Base Morse timing unit in seconds. Dashes are 3 units.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Blink SOS once, restore the LED, then exit without connectivity checks.",
    )
    return parser


def install_signal_handlers() -> None:
    def request_stop(_signum: int, _frame: object) -> None:
        raise StopRequested

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)


def run(args: argparse.Namespace) -> int:
    led = ActivityLed(resolve_led_dir(args.led))
    consecutive_failures = 0

    try:
        if args.test:
            led.sos_once(args.morse_unit)
            return 0

        while True:
            if internet_is_reachable(args.probe, args.timeout):
                consecutive_failures = 0
                led.restore()
                interruptible_sleep(args.interval)
                continue

            consecutive_failures += 1
            if consecutive_failures >= args.fail_threshold:
                led.sos_for(args.interval, args.morse_unit)
            else:
                interruptible_sleep(args.interval)
    except StopRequested:
        return 0
    finally:
        led.restore()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.probe is None:
        args.probe = [
            parse_probe(value)
            for value in env_list("INTERNET_WATCHDOG_PROBES", DEFAULT_PROBES)
        ]
    install_signal_handlers()

    try:
        return run(args)
    except PermissionError as exc:
        print(f"permission error writing ACT LED sysfs files: {exc}", file=sys.stderr)
        print("run this watchdog as root, usually through its systemd unit", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"internet LED watchdog failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
