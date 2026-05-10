from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class TriggerResult:
    accepted: bool
    message: str


class SirenHardware:
    def __init__(self, gpio_pin: int) -> None:
        from gpiozero import DigitalOutputDevice

        self._device = DigitalOutputDevice(gpio_pin, active_high=True, initial_value=False)
        self._lock = threading.Lock()
        self._active = False
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None

    def trigger(self, duration_seconds: float) -> TriggerResult:
        with self._lock:
            if self._active:
                return TriggerResult(accepted=False, message="siren is already active")

            self._active = True
            self._stop_event.clear()
            self._worker = threading.Thread(
                target=self._run_trigger,
                args=(duration_seconds,),
                name="siren-trigger",
                daemon=True,
            )
            self._worker.start()

        return TriggerResult(accepted=True, message="trigger started")

    def _run_trigger(self, duration_seconds: float) -> None:
        try:
            self._device.on()
            deadline = time.monotonic() + duration_seconds
            while time.monotonic() < deadline and not self._stop_event.is_set():
                time.sleep(0.05)
        finally:
            self._device.off()
            with self._lock:
                self._active = False
                self._worker = None

    def shutdown(self) -> None:
        self._stop_event.set()
        worker = self._worker
        if worker and worker.is_alive():
            worker.join(timeout=2.0)

        with self._lock:
            self._device.off()
            self._device.close()
            self._active = False
            self._worker = None
