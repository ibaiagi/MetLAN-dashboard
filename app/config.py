"""
Central configuration for the MetLAN dashboard backend.
"""
import os

LAN_INTERFACES = os.environ.get("LAN_INTERFACES", "eth0").split(",")
