# Pi system config - NAT/DHCP router

Turns the Pi into an actual router between the testbench LAN (`eth0`) and
the dongle (`eth1`, HiLink HTTP API - see the main README and
`context.md` section 2), instead of just a monitoring dashboard. This is
what "insert the SIM and the LAN gets internet" actually needs - the
dashboard's Modem tab only turns the dongle's radio on/off, it never
touched routing.

Three pieces, all standard Debian/Raspberry Pi OS packages (`nftables`,
`dnsmasq`) plus one sysctl flag - nothing custom-built:

| File | Purpose | Installs to |
|---|---|---|
| `nftables.conf` | NAT (masquerade out `eth1`) + forwarding rules (`eth0` <-> `eth1`) + TCP MSS clamp (avoids cellular-MTU blackholes) | `/etc/nftables.conf` |
| `dnsmasq-metlan.conf` | DHCP + DNS server on `eth0` | `/etc/dnsmasq.d/metlan.conf` |
| `dnsmasq-override.conf` | Restart-on-failure for dnsmasq (none by default - see "If something doesn't work") | `/etc/systemd/system/dnsmasq.service.d/override.conf` |
| `60-metlan-forward.conf` | `net.ipv4.ip_forward=1`, otherwise the kernel drops forwarded packets no matter what nftables says | `/etc/sysctl.d/60-metlan-forward.conf` |

## Topology this assumes

```
[testbench PC] --- [switch] --- eth0 (10.42.0.1/24, static)  [Pi]  eth1 (DHCP from dongle, 192.168.8.x) --- [E3372h-607 dongle] --- mobile network
```

Confirmed 2026-09-23: `eth0` is the Pi's built-in NIC, currently a DHCP
client of the house router via the same switch (`192.168.1.21/24`
today). `eth1` is the dongle's own HiLink USB-Ethernet interface, already
getting `192.168.8.100/24` from the dongle's built-in DHCP server (the
documented double-NAT - see `context.md`).

**Testbench LAN uses a new subnet, `10.42.0.0/24`, not `192.168.1.0/24`.**
Deliberate choice, not an oversight: once this config is active the Pi
*is* the DHCP/NAT authority for whatever's on `eth0`, and running that on
the same subnet the house router already uses would risk a rogue-DHCP
conflict if `eth0` ever ends up plugged into the house network again
without thinking about it. A different subnet makes that mistake obvious
immediately (nothing will get an address) instead of silently fighting
the house router. One consequence: **the dashboard's LAN address changes**
- once `eth0` is static, it's reachable at `http://10.42.0.1:8000` from
the testbench, not `.21` anymore (that was only ever the house router's
DHCP lease).

## Before enabling: safety

**Only bring this up while the switch is disconnected from the house
router** (per your plan). The moment `dnsmasq` is running on `eth0`, it
will answer DHCP requests from anything on that switch - fine on the
isolated testbench, actively disruptive on the house LAN (a second DHCP
server handing out addresses alongside the real router). If you ever want
to put the Pi back on the house network for something else, stop these
services first (`sudo systemctl disable --now dnsmasq nftables`) or just
don't enable them at boot until you're sure.

## Setup (run on the Pi)

1. **Install the packages** (only needed once):

   ```bash
   sudo apt update
   sudo apt install -y nftables dnsmasq
   ```

2. **Give `eth0` a static address.** Raspberry Pi OS uses NetworkManager
   by default since the Bookworm release - check which you actually have
   first:

   ```bash
   which nmcli && systemctl is-active NetworkManager
   ```

   If that prints `active`, use `nmcli`:

   ```bash
   sudo nmcli con add type ethernet ifname eth0 con-name metlan-lan \
     ipv4.method manual ipv4.addresses 10.42.0.1/24 ipv4.never-default yes
   sudo nmcli con up metlan-lan
   ```

   (`ipv4.never-default` keeps `eth0` from being picked as the Pi's
   default route - that has to stay `eth1`, toward the dongle/internet.)

   If NetworkManager isn't active (older `dhcpcd`-based image), tell me
   and we'll write the `dhcpcd.conf` version instead rather than guessing
   blind here.

3. **Copy the config files in and enable everything:**

   ```bash
   cd ~/MetLAN-dashboard/system
   sudo cp 60-metlan-forward.conf /etc/sysctl.d/60-metlan-forward.conf
   sudo sysctl --system

   sudo cp nftables.conf /etc/nftables.conf
   sudo systemctl enable --now nftables
   sudo systemctl restart nftables

   sudo cp dnsmasq-metlan.conf /etc/dnsmasq.d/metlan.conf
   sudo mkdir -p /etc/systemd/system/dnsmasq.service.d
   sudo cp dnsmasq-override.conf /etc/systemd/system/dnsmasq.service.d/override.conf
   sudo systemctl daemon-reload
   sudo systemctl enable --now dnsmasq
   sudo systemctl restart dnsmasq
   ```

4. **Verify:**

   ```bash
   sudo sysctl net.ipv4.ip_forward        # expect: net.ipv4.ip_forward = 1
   sudo nft list ruleset                  # expect the tables from nftables.conf
   sudo systemctl status dnsmasq --no-pager
   ```

5. On the testbench PC: renew its DHCP lease (unplug/replug the cable, or
   your OS's "repair connection" - varies by OS) and confirm it gets a
   `10.42.0.x` address with gateway `10.42.0.1`. Then check it can reach
   the internet (once a SIM is inserted and the Modem tab shows
   "connected" - without a SIM this will correctly still fail, same as
   the dongle itself has nothing to route to).

## If something doesn't work

- **Testbench PC gets no address at all**: `sudo systemctl status
  dnsmasq --no-pager` / `journalctl -u dnsmasq -n 50 --no-pager` - most
  likely `eth0` isn't actually at `10.42.0.1` yet (step 2 didn't take) or
  dnsmasq's `interface=eth0` doesn't match reality.
- **Gets an address but no internet**: check `sudo nft list ruleset`
  matches `nftables.conf` (`flush ruleset` at the top of another config
  can silently wipe this one if something else also writes
  `/etc/nftables.conf`), then check `sudo sysctl net.ipv4.ip_forward`
  is actually `1`, then check the Modem tab actually shows "connected"
  (no SIM = dongle has nothing to forward to, expected).
- **Dashboard unreachable after this**: it moved from
  `http://192.168.1.21:8000` to `http://10.42.0.1:8000` - see "Topology
  this assumes" above.
- **Ping/raw IPs work, but nothing by domain name does (browser hangs,
  `nslookup` times out)** - confirmed 2026-09-23: this is dnsmasq, not the
  mobile connection. `sudo systemctl status dnsmasq --no-pager` - if it
  shows `failed` with `unknown interface eth0` in the log, dnsmasq lost a
  startup race against `eth0` coming up (NetworkManager) and, without
  `dnsmasq-override.conf` installed, never retries on its own - it can sit
  dead for hours with everything else looking fine. `bind-dynamic` in
  `dnsmasq-metlan.conf` (not `bind-interfaces`) and the restart-on-failure
  override both exist specifically to stop this recurring; `sudo
  systemctl restart dnsmasq` fixes it immediately either way.
- **A page loads by IP but a real site (e.g. video-heavy ones) hangs** -
  classic cellular-MTU blackhole: a large TCP packet gets silently dropped
  instead of fragmented, because the ICMP "too big" message that's
  supposed to trigger fragmentation doesn't make it back either. The TCP
  MSS clamp in `nftables.conf` (`tcp flags syn tcp option maxseg size set
  rt mtu`) exists specifically for this - confirm it's actually loaded
  with `sudo nft list ruleset` (look for the `inet mangle` table).

## Known open points

- Device names via the dnsmasq lease file (`/var/lib/misc/dnsmasq.leases`)
  - `app/services/network_service.py` still does reverse-DNS only; wiring
    this up is a separate, already-planned follow-up (see main README's
    "Known open points").
  - `dnsmasq-metlan.conf` doesn't set a custom lease file path, so it uses
    the package default above.
- **Live-tested end-to-end 2026-09-23** with an Izarkom SIM (testbench PC
  -> Pi NAT/DHCP -> dongle -> mobile network -> real internet, HTTPS
  included) - see `context.md`'s 2026-09-23 note for the full trail
  (SIM PIN, APN profile, manual `dial()`, dnsmasq crash, MTU blackhole -
  all found and fixed this session). Not yet tested under sustained/heavy
  load, or outdoors at the actual install site.
- No DHCP reservations/static leases configured - fine for a one-PC
  testbench, revisit if the testbench grows more devices that need a
  stable address.
