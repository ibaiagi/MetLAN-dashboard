"""
Central configuration for the MetLAN dashboard backend.
"""
import os

LAN_INTERFACES = os.environ.get("LAN_INTERFACES", "eth0").split(",")

STATS_HISTORY_SAMPLE_INTERVAL_S = int(os.environ.get("STATS_HISTORY_SAMPLE_INTERVAL_S", "60"))
STATS_HISTORY_RETENTION_HOURS = float(os.environ.get("STATS_HISTORY_RETENTION_HOURS", "24"))

# Dongle HiLink HTTP API (app/services/modem_service.py). Optional - the
# unit in use as of 2026-09-23 needs no login at all, but if a password is
# ever set on the dongle, put it in a local .env file (already
# .gitignore'd), never here.
HILINK_HOST = os.environ.get("HILINK_HOST", "192.168.8.1")
HILINK_USER = os.environ.get("HILINK_USER", "admin")
HILINK_PASSWORD = os.environ.get("HILINK_PASSWORD")

# SIM PIN (optional, only needed if the inserted SIM has PIN lock enabled -
# confirmed 2026-09-23 that a locked SIM shows as undetected otherwise).
HILINK_PIN = os.environ.get("HILINK_PIN")

# Real USB port power via uhubctl (app/services/usb_power_service.py) -
# separate from the dongle's own dataswitch, which doesn't cut power to the
# radio (confirmed 2026-09-25, see context.md). The Pi 4's USB ports are
# ganged across two hub trees that must both be switched together for a
# port to actually lose power - confirmed via live testing, don't change
# without re-testing on real hardware.
UHUBCTL_BIN = os.environ.get("UHUBCTL_BIN", "/usr/sbin/uhubctl")
USB_POWER_HUBS = os.environ.get("USB_POWER_HUBS", "2,1-1").split(",")
