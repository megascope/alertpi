# Siren Driver

Minimal Raspberry Pi webhook service that triggers a GPIO-controlled siren or LED toy.

## What it does

- Exposes `POST /trigger`
- Requires bearer-token authentication
- Turns one GPIO pin on for a configurable duration
- Defaults GPIO off and forces it off after every trigger or error path
- Runs well as a dedicated host `siren` user under systemd on Raspberry Pi OS
- Avoids rootless Podman for GPIO because host device passthrough and pin factories were unreliable in practice

## Quick start

1. Run the bootstrap script:

   ```bash
   ./scripts/setup.sh
   ```

   On Raspberry Pi, this auto-installs the Pi GPIO extra. On non-Pi hosts, it installs only the default/dev extras.

2. Create the dedicated service user and its locked-down home/config layout:

   ```bash
   sudo ./scripts/setup-siren-user.sh
   ```

3. If you prefer the manual path, use Python 3.11 for this project:

   ```bash
   uv python install 3.11
   ```

4. Install Python dependencies with `uv` into `.venv`:

   ```bash
   uv sync --python 3.11 --extra dev
   ```

   On Raspberry Pi hardware, install the Pi GPIO extra as well:

   ```bash
   uv sync --python 3.11 --extra dev --extra pi
   ```

5. Create a local environment file:

   ```bash
   cp .env.example .env
   ```

6. Install the host systemd service:

   ```bash
   sudo ./scripts/systemd-install.sh
   ```

7. Start the service locally:

   ```bash
   uv run uvicorn siren_driver.main:app --host 0.0.0.0 --port 8000
   ```

## Authentication

The service expects an HTTP bearer token:

- `Authorization: Bearer <token>`

Set the token with `SIREN_BEARER_TOKEN`.

FastAPI docs expose this directly:

- `http://<host>:<port>/docs` includes an **Authorize** button for bearer token entry.

Example payload:

```json
{"duration_seconds": 3}
```

## Environment

See `.env.example` for the full list of settings.

If you are using the host systemd deployment, the bearer token comes from
`/etc/siren-driver/siren-driver.env`, which is created from `.env.example` by
[`scripts/setup-siren-user.sh`](scripts/setup-siren-user.sh) if it does not
already exist.

The dedicated `siren` account is intentionally locked down:

- `nologin` shell
- no interactive password
- only the `gpio` supplementary group
- private home under `/var/lib/siren-driver`
- config directory under `/etc/siren-driver`

## Localhost testing

Webhook path test (auth + API + GPIO):

1. Start the service:

   ```bash
   uv run uvicorn siren_driver.main:app --host 127.0.0.1 --port 8000
   ```

2. In another terminal, run:

   ```bash
   uv run python scripts/local_trigger.py --token "replace-me" --duration 1.5
   ```

Direct GPIO pulse test (no HTTP):

```bash
uv run python scripts/gpio_smoke.py --pin 17 --duration 1.0
```

If gpiozero reports pin factory fallbacks on Raspberry Pi, force the intended backend:

```bash
GPIOZERO_PIN_FACTORY=lgpio uv run --python 3.11 python scripts/gpio_smoke.py --pin 17 --duration 1.0
```

Mock-only test mode (safe on laptops with no GPIO hardware):

```bash
GPIOZERO_PIN_FACTORY=mock uv run python scripts/gpio_smoke.py --pin 17 --duration 0.2
```

## Host service

This project is designed to run directly on the Pi as a dedicated service user.

Install and enable the service:

```bash
sudo ./scripts/setup-siren-user.sh
sudo ./scripts/systemd-install.sh
```

Check status and logs:

```bash
sudo systemctl status siren-driver.service --no-pager
sudo journalctl -u siren-driver.service -n 50 --no-pager
```

Remove the service:

```bash
sudo ./scripts/systemd-uninstall.sh
sudo ./scripts/systemd-uninstall.sh --purge
```

## Internet LED watchdog

On Raspberry Pi 3, the built-in green ACT LED is normally exposed through
`/sys/class/leds/led0`. This repo includes a small root systemd watchdog that
blinks SOS on that LED only after internet checks fail repeatedly, then restores
the LED's previous kernel trigger when connectivity returns or the service
stops.

Install and enable it:

```bash
sudo ./scripts/internet-watchdog-install.sh
```

Check status and logs:

```bash
sudo systemctl status internet-led-watchdog.service --no-pager
sudo journalctl -u internet-led-watchdog.service -n 50 --no-pager
```

Test the SOS blink pattern once:

```bash
sudo /usr/bin/python3 /opt/siren-driver/src/watchdog/internet_led_watchdog.py --test
```

Optional settings live in `/etc/siren-driver/internet-led-watchdog.env`.
Defaults probe `1.1.1.1:443` and `8.8.8.8:53` every 10 seconds. Blinking
starts after 3 consecutive failed checks. The SOS pattern uses a 0.2 second
Morse timing unit by default.

Remove the service:

```bash
sudo ./scripts/internet-watchdog-uninstall.sh
sudo ./scripts/internet-watchdog-uninstall.sh --purge
```

## Safety notes

- GPIO starts inactive and is driven low on startup.
- Each trigger is serialized so overlapping activations are rejected.
- The service turns the pin off in `finally` blocks and on shutdown.
