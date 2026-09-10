# MetLAN Dashboard

Web dashboard for the MetLAN router project (context.md section 10),
running on the single indoor Raspberry Pi 4. Eventual scope: dongle radio
control (Phase 1 - software-only via ModemManager, no relay/GPIO - see
context.md section 2) and network stats (LAN interfaces, internet
reachability, client list).

**No auth planned for v1** (LAN-trust assumption, per context.md). Do not
expose this port outside the LAN.

## Status

**This is currently a static-only page, being rebuilt from scratch.**
`app/main.py` serves just `app/static/` (title + live date in the
header) - there is no backend API right now. The `routers/`/`services/`
modules that implemented dongle control and network stats (ModemManager
`mmcli` wrapper, `psutil`-based LAN stats) were deliberately removed
while the frontend design gets settled first; they'll be rebuilt once
that's stable. `app/config.py` is a near-empty placeholder for when that
happens.

If you're picking this repo up expecting a working dashboard: there isn't
one yet, just the page shell. See "Known open points" below for what's
still to do.

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
and `pwd` on the Pi) before installing - a mismatch here fails the
service at startup with a `status=203/EXEC` error ("Unable to locate
executable ...") because it's looking for the venv in the wrong place.
This has actually happened during this project's development, so it's
worth the 10-second check rather than assuming the checked-in defaults
are right for your box.

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
  served with `Cache-Control: no-store` (see `app/main.py`'s
  `NoCacheStaticFiles`), so a normal browser reload picks up the change -
  no restart needed, and no incognito/cache-clearing tricks required
  either, unlike earlier in this project before that header existed.

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

**Watch out for old patches re-applying stale content.** Re-running an
earlier `changes.patch` (or applying an outdated one) can silently revert
a file that had since moved on - this has actually happened in this
project more than once. Before trusting a "why isn't my change showing
up" investigation, `cat` the file on the Pi (or re-run `git diff HEAD` on
the dev machine) and confirm it's really the version you think it is.

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
3. **Browser cache** - should no longer be an issue for static files
   given the `no-store` header, but if you're on an old cached copy from
   before that header existed, a plain reload can still reuse it; "Clear
   site data" (DevTools -> Application tab) forces a real re-fetch.
4. **Browser console** (`F12` -> Console) for an actual JS error.
5. `sudo systemctl status metlan-gui` / `journalctl -u metlan-gui -f` for
   backend/service problems specifically.

## Project layout

```
app/
  main.py                - FastAPI app; mounts app/static/ with caching disabled (NoCacheStaticFiles)
  config.py               - near-empty placeholder; was the config for the removed routers/services, kept for the rebuild
  static/
    index.html / app.css / app.js  - title + live date in the header; everything else is being redesigned from scratch
```

No `routers/` or `services/` directories right now - they held the
dongle-control and network-stats API and were removed deliberately while
the frontend gets settled (see "Status" above). There is currently no
`/api/*` endpoint of any kind.

## Known open points (tracked in context.md, not decided here)

- Frontend redesign in progress - only the header (title + date) exists
  so far. The panels described in context.md section 10 (dongle control,
  network stats, LAN clients, activity log) still need designing.
- Backend rebuild - the dongle-control (ModemManager `mmcli`) and
  network-stats (`psutil`) logic needs to be rewritten from scratch once
  the frontend settles on what data it actually needs; it doesn't need to
  be identical to what existed before.
- Phase 2 relay GPIO pin + NO/NC wiring (context.md section 7) - out of
  scope until the Phase 1 software control above is rebuilt.
- No auth - matches the v1 decision, revisit if the LAN-trust assumption
  ever changes (backlog, section 10).
