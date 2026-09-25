"""Dongle on/off control via the E3372h-607's own HiLink HTTP API
(huawei-lte-api) - the dongle ships in HiLink mode and there's no
confirmed-safe way to switch this exact firmware to ModemManager-compatible
Stick mode, so Phase 1 control goes through HiLink's built-in web API
instead (context.md, 2026-09-23 update). Verified live against the actual
unit: no admin password needed on this one for either reading status or
toggling dataswitch, but HILINK_PASSWORD is still supported (optional) in
case that's ever set. A PIN-locked SIM shows as undetected until unlocked -
HILINK_PIN (optional) gets sent via client.pin.operate() on every connect.
This unit's dial-up ConnectMode is manual, not auto (confirmed live
2026-09-23) - enabling the radio alone doesn't dial, so set_power(True)
also calls dial_up.dial(). Disabling does NOT go through mobile-dataswitch:
confirmed live 2026-09-23 that dataswitch reads/writes don't reflect or
control real connection state on this unit (it read 0 while fully
connected). The real disconnect is the same dialup/dial endpoint dial()
uses, with Action=0 instead of 1 - huawei-lte-api has no public hangup(),
so that goes through its low-level session directly. Also confirmed live
2026-09-23: neither dataswitch=0 nor this hangup actually powers down the
radio - the dongle stays registered on the LTE network either way (see
context.md), so this is a data-session on/off, not a real RF disable. The
APN profile itself (Izarkom: APN "internet", blank user/pass, PAP) had to
be set once by hand via the dongle's own HiLink web page - huawei-lte-api
has no clean method for that (it needs RSA-encrypted XML the web UI's own
JS handles), so it's not something this code manages. Same in-memory
action log as before - resets on restart."""
import time

from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection

from app.config import HILINK_HOST, HILINK_USER, HILINK_PASSWORD, HILINK_PIN

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


def _unlock_pin(client: Client) -> None:
    # Best-effort, idempotent: only relevant if the SIM actually needs a
    # PIN. Errors here (already unlocked, no PIN needed, wrong PIN) are
    # swallowed on purpose - the real state still shows up correctly in
    # whatever status/dataswitch call follows this.
    if not HILINK_PIN:
        return
    try:
        client.pin.operate(operate_type="0", current_pin=HILINK_PIN)
    except Exception:
        pass


def get_status() -> dict:
    try:
        with _connect() as connection:
            client = Client(connection)
            _unlock_pin(client)
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
            _unlock_pin(client)
            if enable:
                client.dial_up.set_mobile_dataswitch(dataswitch=1)
                # ConnectMode is manual on this unit - dataswitch alone
                # registers on the network but never dials. Best-effort:
                # dial() erroring (e.g. already connecting) shouldn't fail
                # the whole toggle.
                try:
                    client.dial_up.dial()
                except Exception:
                    pass
            else:
                # dataswitch doesn't control real state on this unit - the
                # actual hangup is dialup/dial Action=0, same endpoint
                # dial() posts Action=1 to. No public method for it.
                client.dial_up._session.post_set("dialup/dial", {"Action": 0})
        _log_action(action, True)
        return {"ok": True, "error": None}
    except Exception as exc:
        _log_action(action, False, str(exc))
        return {"ok": False, "error": str(exc)}


def get_action_log() -> list[dict]:
    return list(reversed(_actions))
