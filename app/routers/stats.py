from fastapi import APIRouter

from app.services import history_service, stats_service

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/throughput")
def throughput():
    return {"interfaces": stats_service.get_interface_stats()}


@router.get("/system")
def system():
    return stats_service.get_system_stats()


@router.get("/history")
def history():
    return history_service.get_history()
