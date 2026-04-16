"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from prom_bench_stats.web import app


client = TestClient(app)


class TestHealth:
    def test_health_endpoint(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["app"] == "SigmaProm"
        assert "prometheus_url" in data


class TestMetricNames:
    def test_metric_names_endpoint(self):
        response = client.get("/api/metric-names")
        assert response.status_code == 200
        data = response.json()
        assert "prometheus_url" in data
        assert "count" in data
        assert "names" in data


class TestDashboard:
    @patch("prom_bench_stats.api.dashboard.query_range", new_callable=AsyncMock)
    @patch("prom_bench_stats.api.dashboard.get_dashboard_object")
    @patch("prom_bench_stats.api.dashboard.iter_grafana_panels")
    def test_render_dashboard_success(self, mock_iter_panels, mock_get_dash, mock_query):
        mock_get_dash.return_value = {"panels": []}
        mock_iter_panels.return_value = [
            {
                "id": 1,
                "title": "Test Panel",
                "type": "graph",
                "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
                "targets": [{"expr": "up", "legendFormat": ""}]
            }
        ]
        mock_query.return_value = {
            "data": {
                "result": [
                    {
                        "metric": {"__name__": "up", "job": "test"},
                        "values": [[1000, "1.0"], [1015, "2.0"]]
                    }
                ]
            }
        }

        response = client.post("/api/grafana/render-dashboard", json={
            "dashboard": {"panels": []},
            "minutes": 30
        })
        assert response.status_code == 200
        data = response.json()
        assert "panels" in data
        assert len(data["panels"]) == 1
        assert data["skipped_boring_targets"] == 0

    @patch("prom_bench_stats.api.dashboard.query_range", new_callable=AsyncMock)
    @patch("prom_bench_stats.api.dashboard.get_dashboard_object")
    @patch("prom_bench_stats.api.dashboard.iter_grafana_panels")
    def test_render_dashboard_skips_flat_series(self, mock_iter_panels, mock_get_dash, mock_query):
        mock_get_dash.return_value = {"panels": []}
        mock_iter_panels.return_value = [
            {
                "id": 1,
                "title": "Flat Panel",
                "type": "graph",
                "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
                "targets": [{"expr": "up", "legendFormat": ""}]
            }
        ]
        mock_query.return_value = {
            "data": {
                "result": [
                    {"metric": {"__name__": "up"}, "values": [[1000, "5.0"], [1015, "5.0"]]}
                ]
            }
        }

        response = client.post("/api/grafana/render-dashboard", json={
            "dashboard": {"panels": []},
            "minutes": 30
        })
        assert response.status_code == 200
        data = response.json()
        assert data["skipped_boring_targets"] == 1
        assert data["panels"] == []

    @patch("prom_bench_stats.api.dashboard.query_range", new_callable=AsyncMock)
    @patch("prom_bench_stats.api.dashboard.get_dashboard_object")
    @patch("prom_bench_stats.api.dashboard.iter_grafana_panels")
    def test_render_dashboard_include_flat_true(self, mock_iter_panels, mock_get_dash, mock_query):
        mock_get_dash.return_value = {"panels": []}
        mock_iter_panels.return_value = [
            {
                "id": 1,
                "title": "Flat Panel",
                "type": "graph",
                "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
                "targets": [{"expr": "up", "legendFormat": ""}]
            }
        ]
        mock_query.return_value = {
            "data": {
                "result": [
                    {"metric": {"__name__": "up"}, "values": [[1000, "5.0"], [1015, "5.0"]]}
                ]
            }
        }

        response = client.post("/api/grafana/render-dashboard", json={
            "dashboard": {"panels": []},
            "minutes": 30,
            "include_flat": True
        })
        assert response.status_code == 200
        data = response.json()
        assert data["skipped_boring_targets"] == 0
        assert len(data["panels"]) == 1

    def test_render_dashboard_invalid_dashboard(self):
        response = client.post("/api/grafana/render-dashboard", json={})
        assert response.status_code == 400
        assert "Provide JSON with a `dashboard` object" in response.json()["detail"]

    def test_render_dashboard_no_panels(self):
        with patch("prom_bench_stats.api.dashboard.get_dashboard_object") as mock_get:
            mock_get.return_value = {"panels": []}
            response = client.post("/api/grafana/render-dashboard", json={
                "dashboard": {"panels": []}
            })
            assert response.status_code == 400
            assert "No panels with Prometheus expr targets" in response.json()["detail"]

    def test_render_dashboard_invalid_time_range(self):
        response = client.post("/api/grafana/render-dashboard", json={
            "dashboard": {"panels": [{"targets": [{"expr": "up"}]}]},
            "from": 2000,
            "to": 1000
        })
        assert response.status_code == 400
        assert "`to` must be later than `from`" in response.json()["detail"]