"""
Connected-devices ("LAN clients") lookup, read from the kernel's
neighbour (ARP) table via `ip -json neigh`.
"""
import json
import socket
import subprocess

from app.config import LAN_INTERFACES


def _resolve_hostname(ip: str) -> str | None:
    try:
        socket.setdefaulttimeout(0.5)
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror, socket.timeout, OSError):
        return None
    finally:
        socket.setdefaulttimeout(None)


def get_lan_clients() -> list[dict]:
    try:
        result = subprocess.run(
            ["ip", "-json", "neigh"], capture_output=True, text=True, timeout=3
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []

    if result.returncode != 0:
        return []

    try:
        entries = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    clients = []
    for entry in entries:
        if entry.get("dev") not in LAN_INTERFACES:
            continue
        ip = entry.get("dst")
        mac = entry.get("lladdr")
        if not ip or not mac:
            # Incomplete/failed neighbour entries - nothing useful to show.
            continue
        clients.append(
            {
                "ip": ip,
                "mac": mac,
                "hostname": _resolve_hostname(ip),
            }
        )
    return clients
