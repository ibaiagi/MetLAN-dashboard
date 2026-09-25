"""Combined ON/OFF control for the dashboard's simple view - orchestrates
usb_power_service.py (real RF power) and modem_service.py (the data
session) into one action, since a regular user shouldn't need to know
these are two separate steps. OFF always does the real USB power cut
(genuine RF-off, not just the data-session toggle - see
usb_power_service.py's docstring). ON powers the USB back on, waits for
the dongle's HiLink API to come back up, then dials - set_power(True) is
called either way once the wait loop ends, so a genuine failure to come
back up still surfaces through modem_service's own action log instead of
disappearing silently. Confirmed live 2026-09-25: a single dial() right
after a fresh power-on often lands while the modem is still mid-attach -
it registers (LED blinking cyan) but never actually connects - so the
dial is retried until ConnectionStatus reports connected instead of
trusting the first call. The granular per-step controls stay reachable
under the dashboard's Advanced section for debugging.
"""
import time

from app.services import modem_service, usb_power_service

_BOOT_POLL_INTERVAL_S = 2
_BOOT_TIMEOUT_S = 30
_CONNECT_POLL_INTERVAL_S = 3
_CONNECT_RETRIES = 6


def get_status() -> dict:
    usb = usb_power_service.get_state()
    if not usb.get("available"):
        return {"power": "unknown", "detail": usb.get("reason")}
    if usb["state"] == "off":
        return {"power": "off", "detail": None}

    modem = modem_service.get_status()
    if not modem.get("available"):
        return {"power": "connecting", "detail": "modem not reachable yet"}
    return {
        "power": "on" if modem["state"] == "connected" else "connecting",
        "detail": modem["state"],
    }


def power_on() -> dict:
    usb_result = usb_power_service.set_state(True)
    if not usb_result["ok"]:
        return usb_result

    deadline = time.monotonic() + _BOOT_TIMEOUT_S
    while time.monotonic() < deadline:
        if modem_service.get_status().get("available"):
            break
        time.sleep(_BOOT_POLL_INTERVAL_S)

    result = modem_service.set_power(True)
    for _ in range(_CONNECT_RETRIES):
        if modem_service.get_status().get("state") == "connected":
            break
        time.sleep(_CONNECT_POLL_INTERVAL_S)
        result = modem_service.set_power(True)
    return result


def power_off() -> dict:
    return usb_power_service.set_state(False)
