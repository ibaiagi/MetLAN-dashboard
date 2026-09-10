from fastapi import APIRouter
from pydantic import BaseModel

from app.services import modem_service, relay_service

router = APIRouter(prefix="/api/dongle", tags=["dongle"])


class PowerRequest(BaseModel):
    state: bool  # true = on, false = off


@router.get("/power")
def get_power():
    return relay_service.get_state()


@router.post("/power")
def set_power(body: PowerRequest):
    return relay_service.set_state(body.state)


@router.get("/log")
def get_log():
    return {"log": relay_service.get_log()}


@router.get("/modem")
def get_modem():
    return modem_service.get_status()
