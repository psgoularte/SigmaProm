"""Dashboard API routes."""

import time
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from prom_bench_stats.grafana_import import get_dashboard_object, iter_grafana_panels, promql_smoothing_hint
from prom_bench_stats.prometheus_fetch import (
    matrix_result_is_uninteresting,
    matrix_to_chartjs,
    matrix_to_per_series_charts,
    query_range,
    range_step_for_window,
)
from prom_bench_stats.settings import prometheus_base_url
from prom_bench_stats.statistical_analysis import analyze_multiple_runs

router = APIRouter()


@router.post("/api/grafana/render-dashboard")
async def grafana_render_dashboard(body: dict[str, Any] = Body(...)):
    """
    Load every Prometheus target from Grafana dashboard JSON, run ``query_range`` for each
    (raw TSDB resolution — no SigmaProm-side smoothing). Layout follows ``gridPos`` (24-col grid).
    """
    def parse_timestamp(value: Any, name: str) -> float:
        if value is None:
            raise ValueError(f"{name} is required when using fixed range")
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError(f"{name} is required when using fixed range")
            try:
                return float(value)
            except ValueError:
                try:
                    from datetime import datetime, timezone

                    dt = datetime.fromisoformat(value)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt.timestamp()
                except ValueError as e:
                    raise ValueError(f"Invalid {name} timestamp: {value}") from e
        raise ValueError(f"Invalid {name} timestamp: {value}")

    step_override = body.get("step")
    if step_override is not None and isinstance(step_override, str) and step_override.strip() == "":
        step_override = None
    if step_override is not None and not isinstance(step_override, str):
        step_override = str(step_override)

    start = body.get("from")
    end = body.get("to")
    if start is not None or end is not None:
        start = parse_timestamp(start, "from")
        end = parse_timestamp(end, "to")
        if end <= start:
            raise HTTPException(status_code=400, detail="`to` must be later than `from`.")
        minutes = (end - start) / 60.0
    else:
        minutes = float(body.get("minutes", 30))
        end_offset_minutes = float(body.get("end_offset_minutes", 0))
        end = time.time() - end_offset_minutes * 60.0
        start = end - minutes * 60.0

    include_flat = body.get("include_flat", False)
    skipped_boring = 0

    dash_payload = body.get("dashboard")
    if dash_payload is None:
        dash_payload = {k: v for k, v in body.items() if k not in ("minutes", "from", "to", "step")}
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

    step_effective = step_override if step_override else range_step_for_window(end - start)

    panels_out: list[dict[str, Any]] = []
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
            # Keep constant series even if they're all zeros (important for benchmarks)
            # Only skip if truly no data points
            if not include_flat and not result:
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
    if not panels_out:
        note_parts.append(
            " No panels to show: all targets failed or there was no Prometheus data. Widen the time window, fix PromQL/variables, or check Prometheus connectivity."
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


@router.post("/api/grafana/statistical-analysis")
async def statistical_analysis(body: dict[str, Any] = Body(...)):
    """
    Perform statistical analysis across multiple benchmark runs.
    Normalizes time series data to relative timeline and calculates mean ± std deviation.
    """
    # Extract parameters
    dashboard = body.get("dashboard")
    runs = body.get("runs", [])
    step = body.get("step")
    num_points = body.get("num_points")  # None enables auto-detection
    
    if not dashboard:
        raise HTTPException(
            status_code=400,
            detail="Dashboard JSON is required"
        )
    
    if not runs:
        raise HTTPException(
            status_code=400,
            detail="Runs list is required"
        )
    
    # Validate runs format
    valid_runs = []
    for run in runs:
        if run.get("status") != "success":
            continue
            
        timestamps = run.get("prometheus_timestamps", {})
        start_ms = timestamps.get("start_ms")
        finish_ms = timestamps.get("finish_ms")
        
        if not start_ms or not finish_ms:
            continue
            
        valid_runs.append(run)
    
    if not valid_runs:
        raise HTTPException(
            status_code=400,
            detail="No valid runs found. Each run must have status='success' and prometheus_timestamps with start_ms and finish_ms"
        )
    
    try:
        results = await analyze_multiple_runs(
            dashboard=dashboard,
            runs=valid_runs,
            step=step,
            num_points=num_points
        )
        
        auto_detected_text = " (auto-detected)" if results.get('auto_detected', False) else ""
        return {
            "success": True,
            "analysis": results,
            "note": f"Statistical analysis completed for {results['total_runs']} runs with {results['num_points']}{auto_detected_text} interpolated points per series."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Statistical analysis failed: {str(e)}"
        )