# MetLAN Dashboard

Web dashboard for the MetLAN router project (context.md section 10),
running on the single indoor Raspberry Pi 4. Eventual scope: dongle radio
control (Phase 1 - software-only via ModemManager, no relay/GPIO - see
context.md section 2) and network stats (LAN interfaces, internet
reachability, connected devices).

**No auth planned for v1** (LAN-trust assumption, per context.md). Do not
expose this port outside the LAN.

## Status

- **Frontend**: header (title + live date) plus one panel so far -
  "Connected devices", listing IP/MAC/device name/vendor for whatever's in
  the Pi's ARP/neighbour table. Everything else described in context.md
  section 10 (dongle control, internet reachability, interface
  throughput, activity log) is still to be built.
- **Backend**: only `app/routers/network.py` +
  `app/services/network_service.py` + `app/services/vendor_service.py`
  exist right now, backing the connected-devices panel. There is no
  dongle-control code (ModemManager/`mmcli`) at all currently - it was
  removed in an earlier reset pending redesign and hasn't been rebuilt
  yet. `app/config.py` only holds what the network service needs
  (`LAN_INTERFACES`).
- The connected-devices list will be mostly empty until DHCP/NAT
  (nftables) is configured on this Pi - that's expected, not a bug, it's
  just reflecting whatever's already on the wire.
- **Device names mostly won't resolve yet, and that's expected too.**
  `name` is currently a reverse-DNS lookup (`socket.gethostbyaddr`),
  which only works if something on the LAN answers PTR queries - nothing
  does right now, since the Pi isn't the DHCP server (your home router
  still is, for the moment). That's *not* the same mechanism your home
  router uses to show a friendly name like "Ibai's galaxy" - that comes
  straight from the DHCP request itself (devices send their own name as
  part of it, via DHCP option 12), which only whoever's actually running
  DHCP ever sees. **Plan (decided, not yet implemented):** once the Pi
  runs its own DHCP server (nftables/dnsmasq, per the open item below),
  switch `network_service.py` to read names straight from the dnsmasq
  lease file (typically `/var/lib/misc/dnsmasq.leases`) instead of/in
  addition to reverse DNS - that's the exact same source your router
  uses today, so it should show the same names. Explicitly decided
  *against* adding mDNS/NetBIOS lookups as a stopgap - not reliable
  enough across device types to be worth the extra dependency and
  complexity before the DHCP work happens anyway.
- **New: a `vendor` column, resolved locally from the device's MAC
  address - works today, regardless of who runs DHCP.** Unlike the
  `name` field above, this doesn't depend on the Pi (or anything else)
  running DHCP at all: `app/services/vendor_service.py` looks the MAC's
  OUI prefix up in a bundled offline snapshot of IEEE's public
  assignment tables (`app/data/oui.tsv` - see that file's header for
  where it came from and how to refresh it), so it works the same on
  the current home network as it will once the Pi takes over DHCP.
  It's a manufacturer name ("Samsung Electronics", "Apple, Inc."), not a
  personal device name - a helpful hint when `name` is empty, not a
  replacement for it. Two things it can't do anything about: a MAC the
  table has never heard of just returns nothing (blank `-` in the UI,
  same as an unresolved name), and a lot of modern phones (iOS 14+,
  Android 10+) use a randomized/private MAC address per network by
  default for privacy - `vendor_service.py` detects that case
  specifically (the "locally administered" bit in the MAC) and reports
  it as "Randomized/private address" rather than a lookup miss, since no
  vendor table could ever answer for one of those.
- Static files *and* API responses are served with `Cache-Control:
  no-store` (see `app/main.py`) - a normal browser reload always picks up
  a change, no incognito/cache-clearing needed.

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

A systemd unit is included (`metlan-gui.service`). **Double-check the
`User` and `WorkingDirectory` in it actually match your setup** (`whoami`
and `pwd` on the Pi) before installing - a mismatch fails the service at
startup with a `status=203/EXEC` error ("Unable to locate executable
...") because it's looking for the venv in the wrong place. This has
actually happened during this project's development.

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

- **Edited backend Python code** (`app/*.py`) **or the bundled data file**
  (`app/data/oui.tsv`): `uvicorn` runs without `--reload` here (fine for a
  background service, but it means it loads everything once at startup),
  so restart the process:

  ```bash
  sudo systemctl restart metlan-gui
  ```

- **Edited a static file** (`index.html`/`app.css`/`app.js`): served with
  `Cache-Control: no-store`, so a normal reload picks it up - no restart
  needed.

Restarting the whole Pi (`sudo reboot`) is essentially never needed for
any of the above.

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
For a small, self-contained change, copying the files directly with `scp`
instead of patching is often simpler:

```powershell
scp app\static\index.html app\static\app.css app\static\app.js metlan@<pi-host>.local:~/MetLAN-dashboard/app/static/
```

**Watch out for old patches re-applying stale content.** Re-running an
earlier `changes.patch` (or applying an outdated one) can silently revert
a file that had since moved on - this has happened repeatedly in this
project, including to this README itself several times. Before trusting
a "why isn't my change showing up" investigation, `cat` the file on the
Pi (or re-run `git diff HEAD` / `git status` on the dev machine) and
confirm it's really the version you think it is - especially right after
committing, which is when a stray local revert is easiest to miss.

### If a change doesn't show up

Roughly in the order to check them:

1. **The file on the Pi doesn't actually match what you meant to send** -
   `cat` it and compare, rather than assuming the transfer worked.
2. **The static files don't agree with each other** - e.g. `index.html`
   referencing `id="foo"` while `app.js` looks for `id="bar"`, or
   `index.html` missing the `<script src="/app.js"></script>` tag
   entirely (this exact thing happened once - a script tag got dropped
   during a rewrite and nothing on the page ever ran, with zero console
   errors, since a script that's never even requested can't throw).
3. **Browser cache** - shouldn't be an issue given the `no-store` header
   on everything, but if you're on an old cached copy from before that
   header existed, "Clear site data" (DevTools -> Application tab) forces
   a real re-fetch where a plain reload might not.
4. **Browser console** (`F12` -> Console) for an actual JS error.
5. `sudo systemctl status metlan-gui` / `journalctl -u metlan-gui -f` for
   backend/service problems specifically.

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/network/clients` | GET | Connected devices from the ARP/neighbour table: `{"clients": [{"ip", "mac", "name", "vendor"}]}` (`name` is best-effort reverse-DNS, often null; `vendor` is a local MAC-OUI lookup, works regardless of DHCP - see "Status" above for both) |

## Project layout

```
app/
  main.py                    - FastAPI app: no-cache middleware + static mount + routers
  config.py                   - LAN_INTERFACES (which interfaces count as "LAN")
  data/
    oui.tsv                    - bundled offline MAC-OUI -> vendor table (see its own header)
  routers/
    network.py                 - /api/network/* endpoints
  services/
    network_service.py         - ip-neigh-based connected-devices lookup, degrades gracefully with no data
    vendor_service.py          - MAC OUI -> vendor name, from app/data/oui.tsv
  static/
    index.html / app.css / app.js  - title + live date header, "Connected devices" panel
```

No dongle-control code (`routers/dongle.py`, `services/modem_service.py`,
`services/relay_service.py`) exists right now - see "Known open points."

## Known open points (tracked in context.md, not decided here)

- Dongle control (ModemManager Phase 1, per context.md section 2) needs
  rebuilding from scratch - removed in an earlier reset, not yet
  recreated.
- More frontend panels per context.md section 10: internet reachability,
  interface throughput, activity log.
- Device names in the connected-devices panel: switch from reverse DNS to
  reading the dnsmasq lease file once the Pi runs its own DHCP server -
  see "Status" above for the full reasoning. Decided against mDNS/NetBIOS
  as an interim fix. (The new `vendor` column is a separate,
  DHCP-independent improvement already implemented - see "Status".)
- `app/data/oui.tsv` will need occasional manual refreshing as new OUI
  blocks get assigned - see the file's own header for how.
- Online/offline state and a device-count summary were considered for the
  connected-devices panel and explicitly left out for now - revisit if
  wanted later.
- Phase 2 relay GPIO pin + NO/NC wiring (context.md section 7) - out of
  scope until dongle control (Phase 1) is rebuilt.
- No auth - matches the v1 decision, revisit if the LAN-trust assumption
  ever changes (backlog, section 10).
