"""Extract PromQL-like strings and Grafana panel layout from dashboard JSON."""

from __future__ import annotations

import re
from typing import Any


def extract_queries_from_grafana_json(obj: Any) -> list[str]:
    """
    Walk exported dashboard JSON and collect ``expr`` / ``expression`` fields
    (Prometheus panels store the query in ``expr``).

    Grafana variables like ``$__rate_interval`` are left as-is; you may need to
    replace them for a standalone Prometheus query.
    """
    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ("expr", "expression") and isinstance(v, str):
                    s = v.strip()
                    if s and s not in found:
                        found.append(s)
                else:
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(obj)
    return found


def get_dashboard_object(payload: Any) -> dict[str, Any] | None:
    """Accept full API export ``{dashboard: {...}}`` or a bare dashboard dict."""
    if not isinstance(payload, dict):
        return None
    if "dashboard" in payload and isinstance(payload["dashboard"], dict):
        return payload["dashboard"]
    if "panels" in payload:
        return payload
    return None


def _normalize_grid_pos(gp: Any) -> dict[str, int]:
    if not isinstance(gp, dict):
        return {"x": 0, "y": 0, "w": 24, "h": 8}
    return {
        "x": int(gp.get("x", 0)),
        "y": int(gp.get("y", 0)),
        "w": max(1, min(24, int(gp.get("w", 24)))),
        "h": max(1, int(gp.get("h", 8))),
    }


def iter_grafana_panels(dashboard: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Flatten dashboard panels (including nested row panels) into drawable entries.

    Each entry: ``title``, ``gridPos``, ``targets`` list of ``{expr, legendFormat}``.
    """
    out: list[dict[str, Any]] = []

    def walk(panel_list: Any) -> None:
        if not isinstance(panel_list, list):
            return
        for p in panel_list:
            if not isinstance(p, dict):
                continue
            if p.get("type") == "row":
                walk(p.get("panels"))
                continue
            targets_raw = p.get("targets") or []
            targets: list[dict[str, str]] = []
            for t in targets_raw:
                if not isinstance(t, dict):
                    continue
                ex = (t.get("expr") or t.get("query") or "").strip()
                if not ex:
                    continue
                targets.append(
                    {
                        "expr": ex,
                        "legendFormat": (t.get("legendFormat") or t.get("legend") or "") or "",
                    }
                )
            if not targets:
                continue
            out.append(
                {
                    "id": p.get("id"),
                    "title": (p.get("title") or "").strip() or "Panel",
                    "type": p.get("type") or "graph",
                    "gridPos": _normalize_grid_pos(p.get("gridPos")),
                    "targets": targets,
                }
            )

    walk(dashboard.get("panels"))
    return out


_RE_SMOOTH = re.compile(
    r"avg_over_time|rolling|smooth|moving_average|median_over_time|quantile_over_time",
    re.IGNORECASE,
)


def promql_smoothing_hint(expr: str) -> str | None:
    """
    If the expression likely applies windowed smoothing in Prometheus, explain that
    SigmaProm cannot recover pre-smoothed raw samples—the query defines the series.
    """
    if _RE_SMOOTH.search(expr):
        return (
            "This expression uses a windowed PromQL function. Prometheus returns values "
            "already computed over that window; SigmaProm plots them as-is. "
            "For the raw underlying metric, edit the query (e.g. use the metric inside without avg_over_time)."
        )
    return None
