#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time

from gpiozero import DigitalOutputDevice


def main() -> int:
    parser = argparse.ArgumentParser(description="Direct GPIO pulse smoke test")
    parser.add_argument("--pin", type=int, default=17, help="GPIO BCM pin number")
    parser.add_argument("--duration", type=float, default=1.0, help="How long to hold the pin high")
    args = parser.parse_args()

    if args.duration <= 0:
        raise SystemExit("--duration must be > 0")

    device = DigitalOutputDevice(args.pin, active_high=True, initial_value=False)
    try:
        print(f"pin {args.pin}: ON")
        device.on()
        time.sleep(args.duration)
    finally:
        device.off()
        device.close()
        print(f"pin {args.pin}: OFF")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
