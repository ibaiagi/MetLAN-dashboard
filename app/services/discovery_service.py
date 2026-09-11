"""Periodic subnet ping sweep, to populate the ARP cache that
network_service.py reads - otherwise devices that never talk to the Pi
directly (most WiFi clients) never show up there."""
import asyncio
import ipaddress
import json
import subprocess

from app.config import LAN_INTERFACES

SWEEP_INTERVAL_S = 30
PING_TIMEOUT_S = 1
PING_CONCURRENCY = 32


def _subnet_hosts(iface: str) -> list[str]:
    try:
        result = subprocess.run(
            ["ip", "-json", "addr", "show", "dev", iface],
            capture_output=True, text=True, timeout=3,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    try:
        entries = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    hosts: list[str] = []
    for entry in entries:
        for addr in entry.get("addr_info", []):
            if addr.get("family") != "inet":
                continue
            local = addr.get("local")
            prefixlen = addr.get("prefixlen")
            if not local or prefixlen is None:
                continue
            net = ipaddress.ip_interface(f"{local}/{prefixlen}").network
            hosts.extend(str(ip) for ip in net.hosts())
    return hosts


async def _ping(ip: str, sem: asyncio.Semaphore) -> None:
    async with sem:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "1", "-W", str(PING_TIMEOUT_S), ip,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()


async def sweep_once() -> None:
    hosts = [ip for iface in LAN_INTERFACES for ip in _subnet_hosts(iface)]
    sem = asyncio.Semaphore(PING_CONCURRENCY)
    await asyncio.gather(*(_ping(ip, sem) for ip in hosts))


async def run_periodic_sweep() -> None:
    while True:
        try:
            await sweep_once()
        except Exception:
            pass
        await asyncio.sleep(SWEEP_INTERVAL_S)
