from fastapi import APIRouter

from app.services import network_service

router = APIRouter(prefix="/api/network", tags=["network"])


@router.get("/clients")
def network_clients():
    """Devices currently visible in the Pi's ARP/neighbour table."""
    return {"clients": network_service.get_lan_clients()}
