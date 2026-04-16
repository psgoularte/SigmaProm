"""Metrics API routes."""

from fastapi import HTTPException, Query

from prom_bench_stats.prometheus_fetch import label_values
from prom_bench_stats.settings import prometheus_base_url

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/metric-names")
async def metric_names(
    limit: int = Query(400, ge=1, le=20000),
    prefix: str = Query("", description="Optional filter: keep names starting with this string"),
):
    try:
        names = await label_values(label_name="__name__")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    names = sorted(n for n in names if n)
    if prefix:
        names = [n for n in names if n.startswith(prefix)]
    return {"prometheus_url": prometheus_base_url(), "count": len(names[:limit]), "names": names[:limit]}