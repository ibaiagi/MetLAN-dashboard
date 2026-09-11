import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import network, stats
from app.services import discovery_service


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(discovery_service.run_periodic_sweep())
    yield
    task.cancel()


app = FastAPI(title="MetLAN Dashboard", lifespan=lifespan)


@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


app.include_router(network.router)
app.include_router(stats.router)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/", NoCacheStaticFiles(directory=STATIC_DIR, html=True), name="static")
