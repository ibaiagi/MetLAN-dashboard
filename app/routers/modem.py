from fastapi import APIRouter, FastAPI

from app.modem_service import modem_check_connection_status, modem_disable, modem_enable, modem_get_logs, client

modem_router = APIRouter(prefix="/api/modem")

@modem_router.get("/status")
async def _get_status():
    return modem_check_connection_status(client)

@modem_router.post("/power")
async def _post_power(enable: bool):
    if enable:
        modem_enable(client)
    else:
        modem_disable(client)

@modem_router.get("/log")
async def _get_logs():
    return modem_get_logs()