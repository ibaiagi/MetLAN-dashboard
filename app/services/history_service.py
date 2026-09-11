"""Long-running CPU/temperature history, persisted to a small SQLite file
so it survives page reloads and the browser tab being closed - unlike the
in-memory throughput chart, which resets on reload."""
import asyncio
import sqlite3
import time
from pathlib import Path

from app.config import STATS_HISTORY_RETENTION_HOURS, STATS_HISTORY_SAMPLE_INTERVAL_S
from app.services import stats_service

_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "history.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS samples (ts REAL NOT NULL, metric TEXT NOT NULL, value REAL NOT NULL)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_samples_ts ON samples(ts)")
    return conn


def record_sample() -> None:
    now = time.time()
    data = stats_service.get_system_stats()

    rows = [(now, "cpu", data["cpu_percent"])]
    for t in data["temperatures"]:
        rows.append((now, f"temp:{t['sensor']}", t["current"]))

    cutoff = now - STATS_HISTORY_RETENTION_HOURS * 3600
    conn = _connect()
    try:
        conn.executemany("INSERT INTO samples (ts, metric, value) VALUES (?, ?, ?)", rows)
        conn.execute("DELETE FROM samples WHERE ts < ?", (cutoff,))
        conn.commit()
    finally:
        conn.close()


def get_history(hours: float | None = None) -> dict:
    cutoff = time.time() - (hours if hours is not None else STATS_HISTORY_RETENTION_HOURS) * 3600
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT ts, metric, value FROM samples WHERE ts >= ? ORDER BY ts", (cutoff,)
        ).fetchall()
    finally:
        conn.close()

    cpu = []
    temperatures: dict[str, list] = {}
    for ts, metric, value in rows:
        ts_ms = ts * 1000
        if metric == "cpu":
            cpu.append([ts_ms, value])
        elif metric.startswith("temp:"):
            temperatures.setdefault(metric[5:], []).append([ts_ms, value])

    return {"cpu": cpu, "temperatures": temperatures}


async def run_periodic_sampling() -> None:
    while True:
        try:
            record_sample()
        except Exception:
            pass
        await asyncio.sleep(STATS_HISTORY_SAMPLE_INTERVAL_S)
