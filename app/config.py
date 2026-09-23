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
