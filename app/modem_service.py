from huawei_lte_api.Connection import Connection
from huawei_lte_api.Client import Client

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

def _init() -> tuple[Connection, Client]:
    conn = Connection(URL)
    status = Client(connection=conn)
    return conn, status

def check_connection_status(client: Client) -> str:
    status = client.monitoring.status()
    if not status["ConnectionStatus"] in STATUS_DICT["ConnectionStatus"]:
        return "Unknown"
    return STATUS_DICT["ConnectionStatus"][status["ConnectionStatus"]]

def enable(client: Client):
    client.dial_up.set_mobile_dataswitch(dataswitch=1)
    client.dial_up.dial()

def disable(client: Client):
    client.dial_up._session.post_set(
        "dialup/dial",
        {
            "Action": 0,
        },
    )

if __name__ == "__main__":
    conn, client = _init()
    print(f" status: {check_connection_status(client)}")
    enable(client)
