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

def _check_connection_status() -> str:
    conn = Connection(URL)
    status = Client(connection=conn).monitoring.status()
    if not status["ConnectionStatus"] in STATUS_DICT["ConnectionStatus"]:
        return "Unknown"
    return STATUS_DICT["ConnectionStatus"][status["ConnectionStatus"]]

if __name__ == "__main__":
    print(f" status: {_check_connection_status()}")