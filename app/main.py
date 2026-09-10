from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


class NoCacheStaticFiles(StaticFiles):
    """
    Serve static files with caching disabled.
    """

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return response


app = FastAPI(title="MetLAN Dashboard")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/", NoCacheStaticFiles(directory=STATIC_DIR, html=True), name="static")
