# MetLAN Dashboard

FastAPI + plain HTML/JS dashboard for the MetLAN router project
(context.md section 10): dongle radio control and network stats, running
on the single indoor Raspberry Pi 4.

**Phase 1 (current):** the dongle's on/off control is software-only, via
ModemManager (`mmcli -m <index> --enable`/`--disable`) - no relay, no
GPIO, no extra hardware. See context.md section 2's Phase 1/Phase 2 note.
The hardware V+ relay disconnect is a deferred Phase 2 upgrade; its
(currently dormant, not wired into any router) code lives in
`app/services/relay_service.py`.

**No auth in v1** (LAN-trust assumption, per context.md). Do not expose
this port outside the LAN.

## Status

- **Frontend is currently a blank slate** (`app/static/`): just the
  "MetLAN" title and a live clock in the header, nothing else. The full
  dashboard UI (dongle control, network stats, LAN clients, activity log)
  is being redesigned from scratch and will be built back up
  incrementally - don't be surprised the page looks empty.
- **The backend API is unaffected and already works** - all endpoints
  below respond normally, they're just not called from the page yet. Any
  frontend work picks back up by fetching them from `app/static/app.js`.
- Network stats (interfaces, internet reachability) work immediately once
  wired in - no extra hardware needed.
- LAN client list will be mostly empty until DHCP/NAT (nftables) is
  configured on this Pi - that's expected, not a bug.
- The dongle endpoints report "not connected" until the Huawei E3372h-607
  is plugged in and ModemManager is installed (`sudo apt install
  modemmanager usb-modeswitch`).

## Running it on the Pi

```bash
cd ~/MetLAN-dashboard   # wherever you actually cloned it - see note below
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then browse to `http://<pi-hostname>.local:8000` from any device on the
LAN.

## Running it as a boot service

A systemd unit is included (`metlan-gui.service`). **The `User` and
`WorkingDirectory` in it are placeholders** (`metlan` /
`/home/metlan/metlan-gui`) - if your actual username or clone path is
different, the service will fail to start with a `status=203/EXEC` error
("Unable to locate executable ...") because it's looking for the venv in
the wrong place. Check with `whoami` and `pwd` on the Pi and edit the file
to match before installing it:

```bash
sudo cp metlan-gui.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now metlan-gui
```

`enable --now` is a one-time setup: it starts the service immediately *and*
registers it to start automatically on every future boot (via a symlink
under `/etc/systemd/system/multi-user.target.wants/`). You don't need to
re-run it after every reboot.

### Applying changes after that

- **Edited `metlan-gui.service` itself** (`User`, `WorkingDirectory`, the
  port): systemd has a cached copy, so it needs to re-read the file before
  restarting:

  ```bash
  sudo systemctl daemon-reload
  sudo systemctl restart metlan-gui
  ```

- **Edited backend Python code** (`app/*.py`): `uvicorn` runs without
  `--reload` here (fine for a background service, but it means it loads
  the code once at startup), so restart the process:

  ```bash
  sudo systemctl restart metlan-gui
  ```

- **Edited a static file** (`index.html`/`app.css`/`app.js`): these are
  served straight from disk by FastAPI's `StaticFiles` on every request -
  **no restart is actually needed** for the server to see the change. If
  a static-file edit doesn't show up in the browser, it is almost always
  the *browser* caching the old file, not the server - see the checklist
  below before assuming anything is broken server-side. Restarting the
  service doesn't hurt and rules the server out, but it's rarely the fix.

Restarting the whole Pi (`sudo reboot`) is essentially never needed for
any of the above - it doesn't do anything `systemctl restart metlan-gui`
doesn't already do for this app, just slower.

Useful for checking things actually worked:

```bash
sudo systemctl status metlan-gui   # is it running, did it crash-loop
journalctl -u metlan-gui -f        # tail its logs live
```

### Deploying code without committing to git yet

If you have local changes on your dev machine you're not ready to commit,
the quickest way to test them on the Pi is a git patch, applied without
committing on either end:

```powershell
# on the dev machine, from the repo root
git diff HEAD > changes.patch
scp changes.patch metlan@<pi-host>.local:~/MetLAN-dashboard/
```

```bash
# on the Pi
cd ~/MetLAN-dashboard
git apply --check changes.patch   # dry run first
git apply changes.patch
sudo systemctl restart metlan-gui
```

Back out cleanly with `git apply -R changes.patch` if it doesn't work out.
For a small, self-contained change (e.g. just the static files), copying
the files directly with `scp` instead of patching is often simpler:

```powershell
scp app\static\index.html app\static\app.css app\static\app.js metlan@<pi-host>.local:~/MetLAN-dashboard/app/static/
```

**Watch out for old patches re-applying stale content.** If you re-run an
earlier `changes.patch` (or `git apply` an outdated one), it can silently
revert a file that had since moved on - this has actually happened in
this project (a CSS fix and this README both got reverted this way).
Before trusting a "why isn't my change showing up" investigation, `cat`
the file on the Pi (or re-run `git diff HEAD` on the dev machine) and
confirm it's really the version you think it is, rather than assuming.

### If a change doesn't show up

Roughly in the order to check them:

1. **Browser cache.** Hard refresh (`Ctrl+Shift+R`) or open in an
   incognito/private window. This alone has explained most "it's not
   working" cases so far.
2. **The file on the Pi doesn't actually match what you meant to send** -
   `cat` it and compare, rather than assuming the transfer worked.
3. **The static files don't agree with each other** - e.g. `index.html`
   referencing `id="foo"` while `app.js` looks for `id="bar"`, or
   `index.html` missing the `<script src="/app.js"></script>` tag
   entirely (this exact thing happened once - a script tag got dropped
   during a rewrite and nothing on the page ever ran, with zero console
   errors, since a script that's never even requested can't throw).
4. **Browser console** (`F12` → Console) for an actual JS error.
5. `sudo systemctl status metlan-gui` / `journalctl -u metlan-gui -f` for
   backend/service problems specifically.

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/dongle/status` | GET | Modem connection state + radio power state + telemetry |
| `/api/dongle/power` | POST `{"state": true\|false}` | Enable/disable the modem radio (Phase 1 on/off) |
| `/api/dongle/log` | GET | Recent dongle-control actions |
| `/api/network/status` | GET | LAN interfaces + internet reachability |
| `/api/network/clients` | GET | LAN client list (ARP table) |

## Project layout

```
app/
  main.py                - FastAPI app, mounts routers + static frontend
  config.py               - hardware/software config (Phase 1 active values, Phase 2 placeholders)
  routers/
    network.py             - /api/network/* endpoints
    dongle.py               - /api/dongle/* endpoints (Phase 1: ModemManager control)
  services/
    network_service.py     - psutil/ip-based LAN stats
    modem_service.py       - mmcli wrapper: status + Phase 1 power control, degrades gracefully with no modem
    relay_service.py       - Phase 2 (dormant) gpiozero wrapper, not imported by any router yet
  static/
    index.html / app.css / app.js  - title + live clock only right now; dashboard UI is being redesigned from scratch
```

## Known open points (tracked in context.md, not decided here)

- Frontend redesign in progress - the panels described in context.md
  section 10 (dongle control, network stats, LAN clients, activity log)
  still need to be rebuilt against the existing API above.
- Phase 2 relay GPIO pin + NO/NC wiring (section 7) - wire
  `relay_service.py` back into `app/routers/dongle.py` once that hardware
  exists.
- No auth - matches the v1 decision, revisit if the LAN-trust assumption
  ever changes (backlog, section 10).
