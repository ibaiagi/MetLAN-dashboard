# MetLAN Dashboard

Web dashboard for the MetLAN router project (context.md section 10),
running on the single indoor Raspberry Pi 4. Eventual scope: dongle radio
control (Phase 1 - software-only via ModemManager, no relay/GPIO - see
context.md section 2) and network stats (LAN interfaces, internet
reachability, connected devices).

**No auth planned for v1** (LAN-trust assumption, per context.md). Do not
expose this port outside the LAN.

## Status

- **Frontend**: header (title + live date+time), a tab switcher, and two
  panels - "Devices" (connected-devices table) and "Statistics"
  (interface throughput). Everything else described in context.md
  section 10 (dongle control, internet reachability, activity log) is
  still to be built.
- **Backend**: `app/routers/network.py` + `app/routers/stats.py` +
  `app/services/network_service.py` + `app/services/vendor_service.py` +
  `app/services/discovery_service.py` + `app/services/stats_service.py`
  exist right now, backing those two panels. There is no dongle-control
  code (ModemManager/`mmcli`) at all currently - it was removed in an
  earlier reset pending redesign and hasn't been rebuilt yet.
  `app/config.py` only holds what the network/stats services need
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
- **A `vendor` column, resolved locally from the device's MAC
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
- **New: WiFi/other devices that never talk to the Pi directly now get
  discovered too, via a background ping sweep.** `ip -json neigh` (what
  `network_service.py` reads) is the kernel's ARP cache - it only knows
  about hosts the Pi has actually exchanged packets with. A phone on the
  home router's WiFi that only ever talks to the router/internet, never
  to the Pi's own address, was invisible before this. `app/services/
  discovery_service.py` now pings every address in each `LAN_INTERFACES`
  subnet every 30s in the background (`app/main.py`'s FastAPI `lifespan`
  starts it at startup), which forces ARP resolution for anything that
  responds - so `ip neigh` (and therefore the connected-devices panel)
  picks it up within ~30s. Needs no extra install: Raspberry Pi OS's
  `ping` binary works unprivileged out of the box. **Residual gap:** a
  device that blocks ICMP ping but still answers ARP won't be caught by
  this - rare for consumer phones/tablets, but possible for some
  security-conscious devices. `arp-scan` would close that gap too, at
  the cost of needing root/`CAP_NET_RAW` - not done for now, see "Known
  open points."
- **New: a "Statistics" tab, next to "Devices", showing live LAN
  interface throughput.** `app/services/stats_service.py` reads
  cumulative rx/tx byte counters per interface via `psutil` (already a
  dependency), and `GET /api/stats/throughput` returns those raw
  counters plus a timestamp - it deliberately doesn't compute a rate
  server-side. `app.js` polls it every second and derives KB/s or MB/s
  from the delta between two consecutive polls (same pattern as
  everything else here: dumb/stateless backend, frontend does the
  polling-based math). The tab switcher itself is plain show/hide with
  `[hidden]` - no routing, no page reload, single `index.html` still.
- **New: a "System" card, below "Interface throughput" in the Statistics
  tab, showing CPU usage and board temperature(s).** `GET
  /api/stats/system` returns overall + per-core CPU percent (from
  `psutil.cpu_percent`) and every temperature sensor `psutil` can find
  (`psutil.sensors_temperatures()`) - on a Pi 4 that's normally just the
  SoC's own thermal zone, labeled something like `cpu_thermal`; if a HAT
  or other add-on exposes more sensors, they show up automatically, no
  code change needed. Degrades to an empty `temperatures` list (shown as
  "Not available" in the UI) if the platform doesn't support it at all,
  rather than erroring. **Explicitly out of scope for now: dongle/modem
  stats (signal, data usage, WAN bandwidth)** - there's no dongle
  connected to this Pi yet, so that's on standby until the dongle-control
  rebuild happens; see "Known open points."
- **New: line-chart history under each Statistics table**, plain
  `<canvas>` drawn by hand in `app.js` - no charting library, works fully
  offline.
  - **Interface throughput**: 5-minute in-memory history (one point per
    1s poll). Lives only in the browser tab and is lost on reload -
    intentional, it changes too fast/is too voluminous to be worth
    logging to disk.
  - **CPU usage and temperature: persisted server-side**, so they no
    longer depend on keeping a browser tab open for hours to see the
    trend. `app/services/history_service.py` samples
    `stats_service.get_system_stats()` once a minute (a background task
    started in `app/main.py`'s lifespan, same pattern as the ping-sweep
    discovery task) and writes it to a small SQLite file
    (`app/data/history.db`, gitignored - it's runtime state, not
    something to commit). Old rows past the retention window are deleted
    on every write. `GET /api/stats/history` returns everything still in
    the window; the frontend re-fetches it once a minute
    (`HISTORY_REFRESH_MS`) and redraws both charts from scratch - no
    client-side accumulation logic needed. Default retention is 24h at a
    1-sample/minute resolution (~1440 rows per metric); both the sample
    interval and retention window are configurable via
    `STATS_HISTORY_SAMPLE_INTERVAL_S` / `STATS_HISTORY_RETENTION_HOURS`
    env vars in `app/config.py`.
  - **CPU and temperature charts have Window/Min/Max controls** (plain
    number inputs above each chart, plus a "Reset" button). By default
    all three are blank, meaning auto: the full fetched window, and the
    Y-axis auto-fit to whatever the data spans. Typing a "Window (h)"
    value re-draws that one chart zoomed to just the last N hours;
    typing Min/Max pins the Y-axis instead of auto-fitting. All of this
    is applied client-side against the already-fetched history (see
    `chartSettings`/`renderCpuChart`/`renderTempChart` in `app.js`), so
    it redraws instantly and doesn't need a new request to the backend -
    it can't show more than what `/api/stats/history` actually returned,
    though (i.e. a Window bigger than the server's retention just shows
    everything available). Settings are per-chart and reset on page
    reload (not persisted) - that's deliberate, this is a "look at this
    right now" control, not a saved preference.
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

**Watch out for old patches re-applying stale content, and for
uncommitted edits silently getting reverted.** Re-running an earlier
`changes.patch` can revert a file that had since moved on. Separately,
this project has also seen edits get discarded on the dev machine before
they were ever committed (cause not confirmed - possibly a `git
checkout`/`restore`/`reset` run without realizing there were uncommitted
changes in the way). **The practical mitigation: commit a change as soon
as you're happy with it, rather than leaving it sitting uncommitted.**
Before trusting a "why isn't my change showing up" investigation, `cat`
the file on the Pi (or re-run `git diff HEAD` / `git status` on the dev
machine) and confirm it's really the version you think it is, and that
it was actually committed.

### If a change doesn't show up

Roughly in the order to check them:

1. **It was never deployed to the Pi at all** - a local commit (or even
   just a local edit) on the dev machine doesn't reach the Pi by itself;
   confirm the `scp`/patch step actually happened.
2. **The file on the Pi doesn't actually match what you meant to send** -
   `cat` it and compare, rather than assuming the transfer worked.
3. **The static files don't agree with each other** - e.g. `index.html`
   referencing `id="foo"` while `app.js` looks for `id="bar"`, or
   `index.html` missing the `<script src="/app.js"></script>` tag
   entirely (this exact thing happened once - a script tag got dropped
   during a rewrite and nothing on the page ever ran, with zero console
   errors, since a script that's never even requested can't throw).
4. **Browser cache** - shouldn't be an issue given the `no-store` header
   on everything, but if you're on an old cached copy from before that
   header existed, "Clear site data" (DevTools -> Application tab) forces
   a real re-fetch where a plain reload might not.
5. **Browser console** (`F12` -> Console) for an actual JS error.
6. `sudo systemctl status metlan-gui` / `journalctl -u metlan-gui -f` for
   backend/service problems specifically.

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/network/clients` | GET | Connected devices from the ARP/neighbour table: `{"clients": [{"ip", "mac", "name", "vendor"}]}` (`name` is best-effort reverse-DNS, often null; `vendor` is a local MAC-OUI lookup, works regardless of DHCP - see "Status" above for both. The ARP table itself is kept warm by a background ping sweep - see "Status".) |
| `/api/stats/throughput` | GET | Per-interface cumulative byte counters: `{"interfaces": [{"interface", "rx_bytes", "tx_bytes", "timestamp"}]}` - raw counters, not a rate; the frontend diffs consecutive polls itself (see "Status"). |
| `/api/stats/system` | GET | CPU + temperature, live snapshot: `{"cpu_percent", "cpu_percent_per_core": [...], "temperatures": [{"sensor", "current", "high", "critical"}]}`. `temperatures` is whatever `psutil.sensors_temperatures()` finds on the box - on a Pi 4 that's normally just the SoC (`cpu_thermal` / similar label), see "Status". |
| `/api/stats/history` | GET | CPU + temperature, persisted history: `{"cpu": [[timestamp_ms, value], ...], "temperatures": {"<sensor>": [[timestamp_ms, value], ...]}}`. Backed by `app/data/history.db` (SQLite), sampled once/minute server-side - see "Status". |

## Project layout

```
app/
  main.py                    - FastAPI app: lifespan-started ping sweep + history sampler + no-cache middleware + static mount + routers
  config.py                   - LAN_INTERFACES, STATS_HISTORY_SAMPLE_INTERVAL_S, STATS_HISTORY_RETENTION_HOURS
  data/
    oui.tsv                    - bundled offline MAC-OUI -> vendor table (see its own header)
    history.db                 - runtime CPU/temperature history (SQLite, gitignored, created on first run)
  routers/
    network.py                 - /api/network/* endpoints
    stats.py                   - /api/stats/* endpoints
  services/
    network_service.py         - ip-neigh-based connected-devices lookup, degrades gracefully with no data
    vendor_service.py          - MAC OUI -> vendor name, from app/data/oui.tsv
    discovery_service.py       - background subnet ping sweep, keeps the ARP cache warm
    stats_service.py           - per-interface rx/tx byte counters + live CPU/temperature snapshot, via psutil
    history_service.py         - persists CPU/temperature samples to app/data/history.db, prunes old rows
  static/
    index.html / app.css / app.js  - title + live date+time header, tab switcher, "Devices"/"Statistics" panels
```

No dongle-control code (`routers/dongle.py`, `services/modem_service.py`,
`services/relay_service.py`) exists right now - see "Known open points."

## Known open points (tracked in context.md, not decided here)

- Dongle control (ModemManager Phase 1, per context.md section 2) needs
  rebuilding from scratch - removed in an earlier reset, not yet
  recreated.
- More frontend panels per context.md section 10: internet reachability,
  activity log. (Interface throughput is now done - see "Status".)
- Device names in the connected-devices panel: switch from reverse DNS to
  reading the dnsmasq lease file once the Pi runs its own DHCP server -
  see "Status" above for the full reasoning. Decided against mDNS/NetBIOS
  as an interim fix. (The `vendor` column is a separate, DHCP-independent
  improvement already implemented - see "Status".)
- `app/data/oui.tsv` will need occasional manual refreshing as new OUI
  blocks get assigned - see the file's own header for how.
- **Ping-sweep discovery (`discovery_service.py`) misses devices that
  block ICMP but still answer ARP.** `arp-scan` would close that gap but
  needs root/`CAP_NET_RAW` (the service currently doesn't run as root) -
  revisit if this turns out to matter in practice.
- Online/offline state and a device-count summary were considered for the
  connected-devices panel and explicitly left out for now - revisit if
  wanted later.
- Phase 2 relay GPIO pin + NO/NC wiring (context.md section 7) - out of
  scope until dongle control (Phase 1) is rebuilt.
- No auth - matches the v1 decision, revisit if the LAN-trust assumption
  ever changes (backlog, section 10).
- Dongle/WAN bandwidth stats (total band usage vs. a configured ceiling,
  to know free bandwidth) - explicitly on standby: no dongle is connected
  to this Pi yet. Revisit once one exists; will need the dongle's WAN
  interface name and either a speed-test-derived or manually configured
  ceiling value.
