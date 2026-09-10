# MetLAN Dashboard (v1 scaffold)

FastAPI + plain HTML/JS dashboard, per context.md section 10's v1 scope:
network stats (interfaces, internet reachability, LAN clients) and dongle
power control (via the GPIO-driven V+ relay) + modem status (via
ModemManager/`mmcli`).

**No auth in v1** (LAN-trust assumption, per context.md). Do not expose this
port outside the LAN.

## Status of this scaffold

Built before the dongle and relay hardware arrived, so it's designed to run
and be testable right now:

- Network stats (interfaces, internet reachability) work immediately - no
  extra hardware needed.
- LAN client list will be mostly empty until DHCP/NAT (nftables) is
  configured on this Pi - that's expected, not a bug.
- Modem panel will show "not connected" until the Huawei E3372h-607 is
  plugged in and ModemManager is installed (`sudo apt install modemmanager
  usb-modeswitch`).
- Dongle power panel will show "unavailable" until a relay is wired to the
  GPIO pin configured in `app/config.py` (**placeholder: BCM17, NO/active-high**
  - update this once the hardware chat confirms the real pin and NO vs NC
  wiring, see context.md section 7).

## Running it on the Pi

```bash
cd ~/metlan-gui
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then browse to `http://<pi-hostname>.local:8000` from any device on the LAN.

GPIO access on Raspberry Pi OS (Bookworm+) needs the running user to be in
the `gpio` group and normally doesn't need root - if `gpiozero` fails to
claim the pin, check `groups $USER` includes `gpio`.

## Running it as a boot service

A systemd unit is included (`metlan-gui.service`). Adjust the `User` and
paths to match your actual setup, then:

```bash
sudo cp metlan-gui.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now metlan-gui
```

## Project layout

```
app/
  main.py              - FastAPI app, mounts routers + static frontend
  config.py             - placeholder hardware config (GPIO pin, etc.)
  routers/
    network.py           - /api/network/* endpoints
    dongle.py             - /api/dongle/* endpoints (power, modem, log)
  services/
    network_service.py   - psutil/ip-based LAN stats
    modem_service.py     - mmcli wrapper, degrades gracefully with no modem
    relay_service.py     - gpiozero wrapper, degrades gracefully with no relay
  static/
    index.html / app.css / app.js  - plain HTML/JS dashboard, polls every 5s
```

## Known open points (tracked in context.md, not decided here)

- Relay GPIO pin + NO/NC wiring (section 7) - update `app/config.py` once closed.
- Whether modem telemetry (signal/operator/data usage) belongs in v1 - the
  `/api/dongle/modem` endpoint already exposes it since it's now "cheap"
  (section 7), but the dashboard card is unconditionally shown; remove/hide
  it if the config/software chat decides to keep it deferred instead.
- No auth - matches the v1 decision, revisit if the LAN-trust assumption
  ever changes (backlog, section 10).
