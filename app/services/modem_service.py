"""Dongle on/off control via the E3372h-607's own HiLink HTTP API
(huawei-lte-api) - the dongle ships in HiLink mode and there's no
confirmed-safe way to switch this exact firmware to ModemManager-compatible
Stick mode, so Phase 1 control goes through HiLink's built-in web API
instead (context.md, 2026-09-23 update). Verified live against the actual
unit: no admin password needed on this one for either reading status or
toggling dataswitch, but HILINK_PASSWORD is still supported (optional) in
case that's ever set. Same in-memory action log as before - resets on
restart."""
import time

from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection

from app.config import HILINK_HOST, HILINK_USER, HILINK_PASSWORD

_ACTION_LOG_CAP = 20
_actions: list[dict] = []

_CONNECTION_STATUS = {
    "900": "connecting",
    "901": "connected",
    "902": "disconnected",
    "903": "disconnecting",
    "904": "connect failed",
}


def _connect() -> Connection:
    # huawei_lte_api.Connection starts an authenticated login session as
    # soon as a username is passed at all, even with no password - only
    # pass credentials when a password is actually set, so this stays
    # anonymous (verified working) until one is.
    if HILINK_PASSWORD:
        return Connection(
            f"http://{HILINK_HOST}/",
            username=HILINK_USER,
            password=HILINK_PASSWORD,
            timeout=5,
        )
    return Connection(f"http://{HILINK_HOST}/", timeout=5)


def get_status() -> dict:
    try:
        with _connect() as connection:
            client = Client(connection)
            dataswitch = client.dial_up.mobile_dataswitch()
            if str(dataswitch.get("dataswitch")) == "0":
                return {"available": True, "state": "disabled"}
            status = client.monitoring.status()
            code = str(status.get("ConnectionStatus"))
            return {"available": True, "state": _CONNECTION_STATUS.get(code, f"unknown ({code})")}
    except Exception:
        return {"available": False, "state": None}


def _log_action(action: str, ok: bool, detail: str = "") -> None:
    _actions.append({"t": time.time() * 1000, "action": action, "ok": ok, "detail": detail})
    if len(_actions) > _ACTION_LOG_CAP:
        del _actions[0]


def set_power(enable: bool) -> dict:
    action = "enable" if enable else "disable"
    try:
        with _connect() as connection:
            client = Client(connection)
            client.dial_up.set_mobile_dataswitch(dataswitch=1 if enable else 0)
        _log_action(action, True)
        return {"ok": True, "error": None}
    except Exception as exc:
        _log_action(action, False, str(exc))
        return {"ok": False, "error": str(exc)}


def get_action_log() -> list[dict]:
    return list(reversed(_actions))
