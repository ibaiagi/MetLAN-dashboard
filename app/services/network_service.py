"""Connected-devices lookup via `ip -json neigh`."""
import json
import socket
import subprocess

from app.config import LAN_INTERFACES
from app.services import vendor_service


def _resolve_name(ip: str) -> str | None:
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
            continue
        clients.append(
            {
                "ip": ip,
                "mac": mac,
                "name": _resolve_name(ip),
                "vendor": vendor_service.lookup_vendor(mac),
            }
        )
    return clients
