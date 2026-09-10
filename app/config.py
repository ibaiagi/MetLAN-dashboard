"""
Central configuration for the MetLAN dashboard backend.

Nothing here is a final hardware decision - values marked "PLACEHOLDER" are
guesses that let the software run and be tested *before* the corresponding
hardware choice (see context.md section 7) is actually closed. Update this
file once the hardware/config decisions land, instead of hunting for magic
numbers throughout the codebase.
"""
import os

# --- Relay / dongle V+ switch -------------------------------------------
# PLACEHOLDER: no relay/MOSFET part or GPIO pin has been chosen yet
# (context.md section 7, "Relay contact wiring" + section 11 "hold off on
# buying"). BCM17 is a common, safe-to-use general purpose pin on the Pi 4
# header, picked only so the software has something to talk to during
# development. Override via the RELAY_GPIO_PIN env var, and update this
# default once hardware design confirms the real pin.
RELAY_GPIO_PIN = int(os.environ.get("RELAY_GPIO_PIN", 17))

# NO (normally-open, default-off) vs NC (normally-closed, default-on) is
# also still an open question in context.md section 7. Defaulting to NO
# (relay energized = dongle powered ON) since "fails de-energized" is the
# safer default for something switching power to a radio transmitter -
# flip this once the hardware chat confirms the actual wiring.
RELAY_ACTIVE_HIGH = os.environ.get("RELAY_ACTIVE_HIGH", "1") != "0"

# --- Modem (ModemManager) ------------------------------------------------
# No dongle is plugged in yet - the modem service is written to degrade
# gracefully (report "not_connected") rather than error out, so the rest
# of the dashboard is usable and testable before the hardware arrives.
MMCLI_BIN = os.environ.get("MMCLI_BIN", "mmcli")

# --- Network stats ---------------------------------------------------------
# Interfaces considered "LAN" for the house-side distribution panel.
# eth0 is the Pi 4's onboard Gigabit port; extend this list once the
# routing/interface plan (nftables, section 10) is finalized.
LAN_INTERFACES = os.environ.get("LAN_INTERFACES", "eth0").split(",")

# How many action-log entries to keep in memory for the dongle power panel.
ACTION_LOG_MAX_ENTRIES = 200
