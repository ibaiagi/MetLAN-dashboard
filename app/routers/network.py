from fastapi import APIRouter

from app.services import network_service

router = APIRouter(prefix="/api/network", tags=["network"])


@router.get("/status")
def network_status():
    return {
        "interfaces": network_service.get_interfaces(),
        "internet": network_service.get_internet_reachability(),
    }


@router.get("/clients")
def network_clients():
    return {"clients": network_service.get_lan_clients()}
