"""Tests for grafana_import module."""

import pytest
from prom_bench_stats.grafana_import import (
    extract_queries_from_grafana_json,
    get_dashboard_object,
    iter_grafana_panels,
    promql_smoothing_hint,
)


class TestExtractQueriesFromGrafanaJson:
    def test_empty_object(self):
        assert extract_queries_from_grafana_json({}) == []

    def test_simple_expr(self):
        obj = {"panels": [{"targets": [{"expr": "up"}]}]}
        assert extract_queries_from_grafana_json(obj) == ["up"]

    def test_multiple_expr(self):
        obj = {
            "panels": [
                {"targets": [{"expr": "up"}, {"expr": "rate(http_requests_total[5m])"}]},
                {"targets": [{"expr": "up"}]}
            ]
        }
        result = extract_queries_from_grafana_json(obj)
        assert "up" in result
        assert "rate(http_requests_total[5m])" in result
        assert len(result) == 2

    def test_expression_field(self):
        obj = {"panels": [{"targets": [{"expression": "down"}]}]}
        assert extract_queries_from_grafana_json(obj) == ["down"]


class TestGetDashboardObject:
    def test_full_export(self):
        payload = {"dashboard": {"panels": []}}
        result = get_dashboard_object(payload)
        assert result == {"panels": []}

    def test_bare_dashboard(self):
        payload = {"panels": []}
        result = get_dashboard_object(payload)
        assert result == {"panels": []}

    def test_invalid(self):
        assert get_dashboard_object("string") is None
        assert get_dashboard_object({}) is None


class TestIterGrafanaPanels:
    def test_empty_dashboard(self):
        dashboard = {"panels": []}
        assert iter_grafana_panels(dashboard) == []

    def test_simple_panel(self):
        dashboard = {
            "panels": [
                {
                    "id": 1,
                    "title": "Test Panel",
                    "type": "graph",
                    "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
                    "targets": [{"expr": "up", "legendFormat": "{{job}}"}]
                }
            ]
        }
        result = iter_grafana_panels(dashboard)
        assert len(result) == 1
        assert result[0]["title"] == "Test Panel"
        assert result[0]["targets"][0]["expr"] == "up"

    def test_row_panel(self):
        dashboard = {
            "panels": [
                {
                    "type": "row",
                    "panels": [
                        {
                            "id": 2,
                            "title": "Sub Panel",
                            "targets": [{"expr": "down"}]
                        }
                    ]
                }
            ]
        }
        result = iter_grafana_panels(dashboard)
        assert len(result) == 1
        assert result[0]["title"] == "Sub Panel"

    def test_panel_without_targets(self):
        dashboard = {
            "panels": [
                {"id": 1, "title": "Empty Panel"}
            ]
        }
        assert iter_grafana_panels(dashboard) == []


class TestPromqlSmoothingHint:
    def test_no_smoothing(self):
        assert promql_smoothing_hint("up") is None
        assert promql_smoothing_hint("rate(http_requests_total)") is None

    def test_with_smoothing(self):
        hint = promql_smoothing_hint("avg_over_time(up[5m])")
        assert hint is not None
        assert "windowed PromQL function" in hint

    def test_case_insensitive(self):
        hint = promql_smoothing_hint("AVG_OVER_TIME(up[5m])")
        assert hint is not None

    def test_other_functions(self):
        assert promql_smoothing_hint("quantile_over_time(0.95, up[5m])") is not None
        assert promql_smoothing_hint("median_over_time(up[5m])") is not None