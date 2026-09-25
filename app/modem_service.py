import os
from huawei_lte_api.Connection import Connection
from huawei_lte_api.Client import Client

HILINK_PIN = os.environ.get("HILINK_PIN")
URL = "http://192.168.8.1"
STATUS_DICT = {
    "ConnectionStatus": {
        "900": "Connecting",
        "901": "Connected",
        "902": "Disconnected",
        "903": "Disconnecting",
        "904": "Connect Failed",
    },
}

def _check_pin(client: Client):
    if HILINK_PIN is None:
        return
    try:
        client.pin.operate(operate_type="0", current_pin=HILINK_PIN)
    except Exception:
        pass

def _init() -> tuple[Connection, Client]:
    conn = Connection(URL)
    client = Client(connection=conn)
    return conn, client

def check_connection_status(client: Client) -> str:
    _check_pin(client)
    status = client.monitoring.status()
    if not status["ConnectionStatus"] in STATUS_DICT["ConnectionStatus"]:
        return "Unknown"
    return STATUS_DICT["ConnectionStatus"][status["ConnectionStatus"]]

def enable(client: Client):
    _check_pin(client)
    client.dial_up.set_mobile_dataswitch(dataswitch=1)
    client.dial_up.dial()

def disable(client: Client):
    _check_pin(client)
    client.dial_up._session.post_set(
        "dialup/dial", {
            "Action": 0,
        },
    )



if __name__ == "__main__":
    conn, client = _init()
