from fastapi import APIRouter

from app.services import usb_power_service

router = APIRouter(prefix="/api/usb-power", tags=["usb-power"])


@router.get("/status")
def status():
    return usb_power_service.get_state()


@router.post("/power")
def power(enable: bool):
    return usb_power_service.set_state(enable)


@router.get("/log")
def log():
    return {"actions": usb_power_service.get_action_log()}
