"""Dongle on/off control via ModemManager's mmcli (Phase 1, context.md
section 2: software radio disable only, no relay/GPIO), plus a short
in-memory action log - resets on restart, same as everything else here."""
import subprocess
import time

_ACTION_LOG_CAP = 20
_actions: list[dict] = []


def _run_mmcli(args: list[str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["mmcli", *args], capture_output=True, text=True, timeout=10
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if result.returncode != 0:
        return False, (result.stderr or result.stdout).strip()
    return True, result.stdout


def _find_modem_index() -> str | None:
    ok, out = _run_mmcli(["-L"])
    if not ok:
        return None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("/org/freedesktop/ModemManager1/Modem/"):
            return line.rsplit("/", 1)[1].split()[0]
    return None


def _parse_state(mmcli_output: str) -> str | None:
    for line in mmcli_output.splitlines():
        line = line.strip()
        if "|" in line:
            line = line.split("|", 1)[1].strip()
        if line.startswith("state:"):
            return line.split(":", 1)[1].strip()
    return None


def get_status() -> dict:
    index = _find_modem_index()
    if index is None:
        return {"available": False, "state": None}

    ok, out = _run_mmcli(["-m", index])
    return {"available": True, "state": _parse_state(out) if ok else None}


def _log_action(action: str, ok: bool, detail: str = "") -> None:
    _actions.append({"t": time.time() * 1000, "action": action, "ok": ok, "detail": detail})
    if len(_actions) > _ACTION_LOG_CAP:
        del _actions[0]


def set_power(enable: bool) -> dict:
    action = "enable" if enable else "disable"
    index = _find_modem_index()
    if index is None:
        _log_action(action, False, "no modem detected")
        return {"ok": False, "error": "No modem detected"}

    ok, out = _run_mmcli(["-m", index, f"--{action}"])
    _log_action(action, ok, "" if ok else out)
    return {"ok": ok, "error": None if ok else out}


def get_action_log() -> list[dict]:
    return list(reversed(_actions))
