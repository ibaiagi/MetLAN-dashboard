from fastapi import APIRouter

from app.services import stats_service

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/throughput")
def throughput():
    return {"interfaces": stats_service.get_interface_stats()}


@router.get("/system")
def system():
    return stats_service.get_system_stats()
