"""Web API: reads metrics from your benchmark project's Prometheus HTTP API and plots them."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from prom_bench_stats.grafana_import import (
    extract_queries_from_grafana_json,
    get_dashboard_object,
    iter_grafana_panels,
    promql_smoothing_hint,
)
from prom_bench_stats.prometheus_fetch import (
    instant_query,
    label_values,
    matrix_result_is_uninteresting,
    matrix_to_chartjs,
    matrix_to_per_series_charts,
    query_range,
    range_step_for_window,
)
from prom_bench_stats.settings import prometheus_base_url, web_port

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="SigmaProm", version="0.1.0")


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "app": "SigmaProm",
        "web_port": web_port(),
        "prometheus_url": prometheus_base_url(),
        "note": "Set PROMETHEUS_URL in .env to the Prometheus your benchmarks use.",
    }


@app.get("/api/diagnostics")
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


@app.get("/api/metric-names")
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


@app.post("/api/grafana/dashboard-queries")
async def grafana_dashboard_queries(payload: Any = Body(...)):
    """Parse pasted Grafana dashboard export JSON; return distinct panel query strings."""
    if not isinstance(payload, (dict, list)):
        raise HTTPException(
            status_code=400,
            detail="Body must be a JSON object or array (paste the full dashboard export).",
        )
    queries = extract_queries_from_grafana_json(payload)
    return {
        "count": len(queries),
        "queries": queries,
        "hint": "Queries may include Grafana variables ($job, $__interval, …). Edit them for plain Prometheus if a query fails.",
    }


@app.post("/api/grafana/render-dashboard")
async def grafana_render_dashboard(body: dict[str, Any] = Body(...)):
    """
    Load every Prometheus target from Grafana dashboard JSON, run ``query_range`` for each
    (raw TSDB resolution — no SigmaProm-side smoothing). Layout follows ``gridPos`` (24-col grid).
    """
    minutes = float(body.get("minutes", 30))
    step_override = body.get("step")
    if step_override is not None and isinstance(step_override, str) and step_override.strip() == "":
        step_override = None
    if step_override is not None and not isinstance(step_override, str):
        step_override = str(step_override)

    dash_payload = body.get("dashboard")
    if dash_payload is None:
        dash_payload = {k: v for k, v in body.items() if k not in ("minutes", "step")}
    dash = get_dashboard_object(dash_payload)
    if not dash:
        raise HTTPException(
            status_code=400,
            detail="Provide JSON with a `dashboard` object or top-level `panels` (Grafana export).",
        )
    panels_spec = iter_grafana_panels(dash)
    if not panels_spec:
        raise HTTPException(
            status_code=400,
            detail="No panels with Prometheus expr targets found (check datasource / panel types).",
        )

    include_flat = bool(body.get("include_flat", False))

    end = time.time()
    start = end - minutes * 60.0
    step_effective = step_override if step_override else range_step_for_window(end - start)

    panels_out: list[dict[str, Any]] = []
    skipped_boring = 0
    for panel in panels_spec:
        targets_out: list[dict[str, Any]] = []
        for tgt in panel["targets"]:
            expr = tgt["expr"]
            ph = promql_smoothing_hint(expr)
            try:
                payload = await query_range(
                    query=expr,
                    start_unix=start,
                    end_unix=end,
                    step=step_override,
                )
            except ValueError as e:
                targets_out.append(
                    {
                        "expr": expr,
                        "legendFormat": tgt.get("legendFormat", ""),
                        "error": str(e),
                        "smoothing_hint": ph,
                    }
                )
                continue
            except Exception as e:
                targets_out.append(
                    {
                        "expr": expr,
                        "legendFormat": tgt.get("legendFormat", ""),
                        "error": f"Prometheus unreachable: {e}",
                        "smoothing_hint": ph,
                    }
                )
                continue
            data = payload.get("data") or {}
            result = data.get("result") or []
            if not include_flat and matrix_result_is_uninteresting(result):
                skipped_boring += 1
                continue
            total_points = sum(len(item.get("values") or []) for item in result)
            targets_out.append(
                {
                    "expr": expr,
                    "legendFormat": tgt.get("legendFormat", ""),
                    "smoothing_hint": ph,
                    "step": step_effective,
                    "series_count": len(result),
                    "total_points": total_points,
                    "chart": matrix_to_chartjs(result),
                    "per_series": matrix_to_per_series_charts(result),
                }
            )
        if not targets_out:
            continue
        panels_out.append(
            {
                "id": panel.get("id"),
                "title": panel["title"],
                "type": panel.get("type"),
                "gridPos": panel["gridPos"],
                "targets": targets_out,
            }
        )

    note_parts = [
        "SigmaProm does not add moving averages. Each plot is Prometheus query_range output at the "
        "given step. PromQL window functions (e.g. avg_over_time) define smoothing inside Prometheus. "
        "Grafana UI-only transforms (e.g. moving average in the panel editor) are not in this JSON and are not applied.",
    ]
    if skipped_boring and not include_flat:
        note_parts.append(
            f" Omitted {skipped_boring} target(s) with no data, all zeros, or a flat constant line."
        )
    if not panels_out:
        note_parts.append(
            " No panels to show: all targets were omitted as flat/empty, or all queries failed—"
            "widen the time window, fix PromQL/variables, or enable “Show flat/empty” (include_flat)."
        )

    return {
        "minutes": minutes,
        "start": start,
        "end": end,
        "step": step_effective,
        "prometheus_url": prometheus_base_url(),
        "panels": panels_out,
        "skipped_boring_targets": skipped_boring,
        "include_flat": include_flat,
        "note": "".join(note_parts),
    }


@app.get("/api/range")
async def api_range(
    query: str = Query(..., description="PromQL expression"),
    minutes: float = Query(60, ge=0.1, le=365 * 24 * 60, description="Last N minutes"),
    step: Optional[str] = Query(
        None,
        description='Optional step override (e.g. "5s") for finer raw samples over the window',
    ),
):
    end = time.time()
    start = end - minutes * 60.0
    step_effective = step if (step and step.strip()) else range_step_for_window(end - start)
    try:
        payload = await query_range(
            query=query,
            start_unix=start,
            end_unix=end,
            step=step if (step and step.strip()) else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Prometheus unreachable: {e}") from e
    data = payload.get("data") or {}
    result = data.get("result") or []
    total_points = sum(len(item.get("values") or []) for item in result)
    chart = matrix_to_chartjs(result)
    per_series = matrix_to_per_series_charts(result)
    return {
        "query": query,
        "start": start,
        "end": end,
        "minutes": minutes,
        "step": step_effective,
        "series_count": len(result),
        "total_points": total_points,
        "prometheus_url": prometheus_base_url(),
        "chart": chart,
        "per_series": per_series,
    }


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    index_path = STATIC_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)
