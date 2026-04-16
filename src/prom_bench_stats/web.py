"""Web API: reads metrics from your benchmark project's Prometheus HTTP API and plots them."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from prom_bench_stats.api import dashboard, health, metrics
from prom_bench_stats.settings import web_port

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="SigmaProm", version="0.1.0")

app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(dashboard.router)


@app.get("/")
async def index():
    index_path = STATIC_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
