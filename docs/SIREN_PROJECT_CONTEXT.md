# Siren Driver project context

Goal: Raspberry Pi 3B triggers an LED/siren toy from a webhook.

Hardware:
- Raspberry Pi 3B
- LED siren toy originally powered by 2xAA, about 3V, ~150mA load
- DRV8833 motor driver board; board labels motor supply as VCC, not VM
- Pi 5V rail feeds a buck converter down to ~3.3V
- Buck output powers DRV8833 VCC and the siren toy load
- 100uF capacitor across DRV8833 supply: positive to VCC, negative to GND
- IN2 is planned to be tied to GND to prevent reverse voltage
- GPIO drives IN1 only
- Common ground between Pi, buck, DRV8833

Networking/security:
- Raspberry Pi OS
- Prefer a dedicated host `siren` user and systemd service for GPIO reliability
- Rootless containers were not suitable for GPIO access in practice; the service should run directly on the host
- Device may be exposed via Cloudflare/PagerDuty webhook
- Need API-key/HMAC-style app auth because PagerDuty may not support Cloudflare Access service token headers
- Wi-Fi can be preconfigured with NetworkManager/nmcli

Known nmcli pattern:
```bash
sudo nmcli connection add \
  type wifi \
  con-name "internet" \
  ifname wlan0 \
  ssid "internet"

sudo nmcli connection modify "internet" \
  wifi-sec.key-mgmt wpa-psk \
  wifi-sec.psk "WIFI_PASSWORD"

sudo nmcli connection modify "internet" \
  connection.autoconnect yes
