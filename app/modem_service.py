import os
from datetime import datetime
from huawei_lte_api.Connection import Connection
from huawei_lte_api.Client import Client
from zoneinfo import ZoneInfo

_HILINK_PIN = os.environ.get("HILINK_PIN")
_URL = "http://192.168.8.1"
_STATUS_DICT = {
    "ConnectionStatus": {
        "900": "Connecting",
        "901": "Connected",
        "902": "Disconnected",
        "903": "Disconnecting",
        "904": "Connect Failed",
    },
}

_logs = {"modem": {}}

def _get_time() -> str:
    now = datetime.now(ZoneInfo("Europe/Madrid"))
    return now.strftime("%Y-%m-%d %H:%M:%S")

def _check_pin(client: Client):
    if _HILINK_PIN is None:
        return
    try:
        client.pin.operate(operate_type="0", current_pin=_HILINK_PIN)
    except Exception:
        pass

def _init() -> tuple[Connection, Client]:
    conn = Connection(_URL)
    client = Client(connection=conn)
    return conn, client
conn, client = _init()

def modem_check_connection_status(client: Client) -> str:
    _check_pin(client)
    status = client.monitoring.status()
    if not status["ConnectionStatus"] in _STATUS_DICT["ConnectionStatus"]:
        _logs["modem"] |= {_get_time(): "Unknown status"}
        return "Unknown"
    out = _STATUS_DICT["ConnectionStatus"][status["ConnectionStatus"]]
    _logs["modem"] |= {_get_time(): out}
    return out

def modem_enable(client: Client) -> None:
    _check_pin(client)
    client.dial_up.set_mobile_dataswitch(dataswitch=1)
    client.dial_up.dial()
    _logs["modem"] |= {_get_time(): "Modem Enable Request sent"}

def modem_disable(client: Client) -> None:
    _check_pin(client)
    client.dial_up._session.post_set(
        "dialup/dial", {
            "Action": 0,
        },
    )
    _logs["modem"] |= {_get_time(): "Modem Disable Request sent"}

def modem_get_logs() -> dict:
    return _logs