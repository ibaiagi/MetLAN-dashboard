from fastapi import APIRouter

from app.services import modem_service

router = APIRouter(prefix="/api/modem", tags=["modem"])


@router.get("/status")
def status():
    return modem_service.get_status()


@router.post("/power")
def power(enable: bool):
    return modem_service.set_power(enable)


@router.get("/log")
def log():
    return {"actions": modem_service.get_action_log()}
