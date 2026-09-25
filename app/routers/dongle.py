from fastapi import APIRouter

from app.services import dongle_control

router = APIRouter(prefix="/api/dongle", tags=["dongle"])


@router.get("/status")
def status():
    return dongle_control.get_status()


@router.post("/power")
def power(enable: bool):
    return dongle_control.power_on() if enable else dongle_control.power_off()
