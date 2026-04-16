"""Health and diagnostics API routes."""

from typing import Any

from fastapi import APIRouter

from prom_bench_stats.prometheus_fetch import instant_query, label_values
from prom_bench_stats.settings import prometheus_base_url

router = APIRouter()


@router.get("/api/health")
async def health():
    return {
        "ok": True,
        "app": "SigmaProm",
        "prometheus_url": prometheus_base_url(),
        "note": "Set PROMETHEUS_URL in .env to the Prometheus your benchmarks use.",
    }


@router.get("/api/diagnostics")
async def diagnostics():
    """Check that we can reach Prometheus and that it has scraped series (helps debug empty graphs)."""
    base = prometheus_base_url()
    out: dict[str, Any] = {
        "prometheus_url": base,
        "reachable": False,
        "instant_up_series": None,
        "metric_names_sample": [],
    }
    try:
        p = await instant_query(query="up")
        res = p.get("data", {}).get("result") or []
        out["reachable"] = True
        out["instant_up_series"] = len(res)
    except Exception as e:
        out["error"] = str(e)
        return out
    try:
        names = await label_values(label_name="__name__")
        names = sorted(names)
        out["metric_name_count"] = len(names)
        out["metric_names_sample"] = names[:40]
    except Exception as e:
        out["label_api_error"] = str(e)
    return out