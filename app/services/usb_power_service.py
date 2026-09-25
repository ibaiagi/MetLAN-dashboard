"""Real USB port power for the dongle, via uhubctl - not a config bit like
modem_service.py's dataswitch, actual VBUS on/off (context.md, 2026-09-25:
confirmed dataswitch=0 and the dialup/dial Action=0 hangup both leave the
dongle registered on LTE, only cutting USB power stops the radio - LED goes
fully dark, confirmed live). On the Pi 4 all 4 USB ports are ganged and
split across two hub trees (the xHCI hub "2" and its USB2 companion "1-1")
that must both be switched for a port to actually lose power - confirmed
live. Needs a sudoers NOPASSWD rule for uhubctl since metlan-gui.service
runs as the non-root "metlan" user. Fails soft like modem_service: uhubctl
missing, no sudoers rule, or no hub attached all report as unavailable
instead of raising. Powering the USB back on does not restart the mobile
data session by itself - that's still modem_service.set_power(True).
"""
import subprocess
import time

from app.config import UHUBCTL_BIN, USB_POWER_HUBS

_ACTION_LOG_CAP = 20
_actions: list[dict] = []


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["sudo", UHUBCTL_BIN, *args],
        capture_output=True,
        text=True,
        timeout=10,
    )


def _log_action(action: str, ok: bool, detail: str = "") -> None:
    _actions.append({"t": time.time() * 1000, "action": action, "ok": ok, "detail": detail})
    if len(_actions) > _ACTION_LOG_CAP:
        del _actions[0]


def get_state() -> dict:
    try:
        # Both hub trees are always switched together by set_state(), so
        # querying the first one is representative.
        result = _run(["-l", USB_POWER_HUBS[0]])
        if result.returncode != 0:
            return {"available": False, "state": None, "reason": result.stderr.strip()}
        # uhubctl prints "power" on a port's status line when it's on, and
        # only the raw hex flags (no "power" word) when it's off.
        state = "on" if "power" in result.stdout else "off"
        return {"available": True, "state": state}
    except Exception as exc:
        return {"available": False, "state": None, "reason": str(exc)}


def set_state(turn_on: bool) -> dict:
    action = "power on" if turn_on else "power off"
    flag = "1" if turn_on else "0"
    try:
        for hub in USB_POWER_HUBS:
            result = _run(["-l", hub, "-a", flag])
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or f"uhubctl exited {result.returncode}")
        _log_action(action, True)
        return {"ok": True, "error": None}
    except Exception as exc:
        _log_action(action, False, str(exc))
        return {"ok": False, "error": str(exc)}


def get_action_log() -> list[dict]:
    return list(reversed(_actions))
