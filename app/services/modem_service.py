"""
Reads modem status via `mmcli` (ModemManager's CLI), which now runs
directly on the same Pi 4 as this dashboard (context.md section 2/7 -
"modem telemetry is now trivially available" since there's no longer a
separate device in between).

No dongle is plugged in yet, so every function here is expected to return
a "not_connected" style result during development - that's the normal,
expected state until the Huawei E3372h-607 (context.md section 11)
actually arrives and is plugged in.
"""
import json
import subprocess

from app.config import MMCLI_BIN


def _run(args: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(
            [MMCLI_BIN, *args],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode, result.stdout
    except FileNotFoundError:
        return -1, ""
    except subprocess.TimeoutExpired:
        return -2, ""


def get_status() -> dict:
    """Return modem status, or a clear 'not_connected' shape if there is none."""
    code, out = _run(["-L", "-J"])

    if code == -1:
        return {"connected": False, "reason": "ModemManager (mmcli) is not installed"}
    if code == -2:
        return {"connected": False, "reason": "mmcli timed out"}
    if code != 0:
        return {"connected": False, "reason": "mmcli returned an error"}

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"connected": False, "reason": "could not parse mmcli output"}

    modem_paths = data.get("modem-list", [])
    if not modem_paths:
        return {"connected": False, "reason": "no modem detected"}

    modem_index = modem_paths[0].rsplit("/", 1)[-1]
    code, out = _run(["-m", modem_index, "-J"])
    if code != 0:
        return {"connected": False, "reason": "mmcli could not query the modem"}

    try:
        modem = json.loads(out).get("modem", {})
    except json.JSONDecodeError:
        return {"connected": False, "reason": "could not parse modem details"}

    generic = modem.get("generic", {})
    signal = modem.get("3gpp", {})

    return {
        "connected": True,
        "modem_index": modem_index,
        "state": generic.get("state"),
        "operator": signal.get("operator-name"),
        "signal_quality_percent": (generic.get("signal-quality", {}) or {}).get("value"),
        "access_technology": generic.get("access-technologies"),
    }
