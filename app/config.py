"""
Central configuration for the MetLAN dashboard backend.
"""
import os

LAN_INTERFACES = os.environ.get("LAN_INTERFACES", "eth0").split(",")

STATS_HISTORY_SAMPLE_INTERVAL_S = int(os.environ.get("STATS_HISTORY_SAMPLE_INTERVAL_S", "60"))
STATS_HISTORY_RETENTION_HOURS = float(os.environ.get("STATS_HISTORY_RETENTION_HOURS", "24"))
