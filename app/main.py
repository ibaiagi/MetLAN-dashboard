from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import network


class NoCacheStaticFiles(StaticFiles):
    """
    Serve static files with caching disabled.
    """

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return response


app = FastAPI(title="MetLAN Dashboard")


@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    """Apply the same no-cache policy to API responses as NoCacheStaticFiles
    applies to static files - the dashboard polls these endpoints, so a
    browser-cached JSON response would show stale data the same way a
    cached app.js once did."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


app.include_router(network.router)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/", NoCacheStaticFiles(directory=STATIC_DIR, html=True), name="static")
