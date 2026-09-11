"""LAN interface throughput and system (CPU/temperature) stats, from
psutil. Interface counters are cumulative since boot - the frontend
derives a rate by diffing two consecutive polls."""
import time

import psutil

from app.config import LAN_INTERFACES


def get_interface_stats() -> list[dict]:
    counters = psutil.net_io_counters(pernic=True)
    now = time.time()
    stats = []
    for iface in LAN_INTERFACES:
        c = counters.get(iface)
        if c is None:
            continue
        stats.append(
            {
                "interface": iface,
                "rx_bytes": c.bytes_recv,
                "tx_bytes": c.bytes_sent,
                "timestamp": now,
            }
        )
    return stats


def get_temperature_stats() -> list[dict]:
    try:
        raw = psutil.sensors_temperatures()
    except (AttributeError, NotImplementedError, OSError):
        return []

    temps = []
    for chip, entries in raw.items():
        for entry in entries:
            temps.append(
                {
                    "sensor": entry.label or chip,
                    "current": entry.current,
                    "high": entry.high,
                    "critical": entry.critical,
                }
            )
    return temps


def get_system_stats() -> dict:
    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "cpu_percent_per_core": psutil.cpu_percent(interval=None, percpu=True),
        "temperatures": get_temperature_stats(),
    }
