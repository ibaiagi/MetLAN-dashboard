"""
House-side LAN network stats (context.md section 10 v1 scope: "Ethernet/LAN
status for the house-side distribution, internet reachability, LAN client
list, throughput").

Uses psutil for interface/throughput stats (portable, no shelling out) and
`ip neigh` for the client list, since NAT/DHCP (nftables) hasn't been
configured on this Pi yet - until it is, this will just reflect whatever's
already on the wire, which is expected during development.
"""
import socket
import subprocess
import time

import psutil

from app.config import LAN_INTERFACES

# Used to compute throughput as a rate rather than a raw byte counter.
_last_sample: dict[str, tuple[float, int, int]] = {}


def get_interfaces() -> list[dict]:
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    counters = psutil.net_io_counters(pernic=True)
    now = time.time()

    interfaces = []
    for name, if_stats in stats.items():
        if name == "lo":
            continue

        ipv4 = next(
            (a.address for a in addrs.get(name, []) if a.family == socket.AF_INET),
            None,
        )

        rx_rate = tx_rate = None
        if name in counters:
            rx_bytes = counters[name].bytes_recv
            tx_bytes = counters[name].bytes_sent
            prev = _last_sample.get(name)
            if prev:
                prev_time, prev_rx, prev_tx = prev
                elapsed = max(now - prev_time, 0.001)
                rx_rate = round((rx_bytes - prev_rx) / elapsed, 1)
                tx_rate = round((tx_bytes - prev_tx) / elapsed, 1)
            _last_sample[name] = (now, rx_bytes, tx_bytes)

        interfaces.append(
            {
                "name": name,
                "role": "lan" if name in LAN_INTERFACES else "other",
                "is_up": if_stats.isup,
                "speed_mbps": if_stats.speed or None,
                "ipv4": ipv4,
                "rx_bytes_per_sec": rx_rate,
                "tx_bytes_per_sec": tx_rate,
            }
        )
    return interfaces


def get_internet_reachability(host: str = "1.1.1.1", timeout_s: float = 2.0) -> dict:
    try:
        start = time.monotonic()
        with socket.create_connection((host, 53), timeout=timeout_s):
            latency_ms = round((time.monotonic() - start) * 1000, 1)
        return {"reachable": True, "latency_ms": latency_ms, "probe_host": host}
    except OSError as exc:
        return {"reachable": False, "error": str(exc), "probe_host": host}


def get_lan_clients() -> list[dict]:
    """
    Best-effort LAN client list via the kernel's neighbour (ARP) table.
    Becomes meaningful once DHCP is actually served from this Pi (section
    10) - for now it just shows whatever's already been seen on the wire.
    """
    try:
        result = subprocess.run(
            ["ip", "-json", "neigh"], capture_output=True, text=True, timeout=3
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []

    if result.returncode != 0:
        return []

    import json

    try:
        entries = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    clients = []
    for entry in entries:
        if entry.get("dev") not in LAN_INTERFACES:
            continue
        clients.append(
            {
                "ip": entry.get("dst"),
                "mac": entry.get("lladdr"),
                "state": entry.get("state", [None])[0],
            }
        )
    return clients
