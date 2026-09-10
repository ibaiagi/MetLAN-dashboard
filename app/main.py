from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import dongle, network

app = FastAPI(title="MetLAN Dashboard")

app.include_router(network.router)
app.include_router(dongle.router)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
