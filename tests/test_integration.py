"""Integration tests for the complete workflow."""

import json
import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from prom_bench_stats.generate_plots import main
from prom_bench_stats.plotting import process_grafana_dashboard


class TestIntegrationWorkflow:
    """Test complete integration workflows."""

    def setup_method(self):
        """Set up test data for integration tests."""
        self.sample_dashboard = {
            "dashboard": {
                "panels": [
                    {
                        "id": 1,
                        "title": "CPU Usage",
                        "type": "graph",
                        "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
                        "targets": [
                            {"expr": "rate(process_cpu_seconds_total[5m])", "legendFormat": "CPU Rate"}
                        ]
                    },
                    {
                        "id": 2,
                        "title": "Memory Usage",
                        "type": "graph",
                        "gridPos": {"x": 12, "y": 0, "w": 12, "h": 8},
                        "targets": [
                            {"expr": "process_resident_memory_bytes", "legendFormat": "Memory"}
                        ]
                    }
                ]
            }
        }
        
        self.sample_intervals = [
            {
                "status": "success",
                "prometheus_timestamps": {
                    "start_ms": 1000000,
                    "finish_ms": 1000600  # 10 minutes
                },
                "readable": {
                    "start": "2026-04-18T04:55:54Z",
                    "finish": "2026-04-18T05:05:54Z",
                    "duration_ms": 600000
                }
            },
            {
                "status": "success",
                "prometheus_timestamps": {
                    "start_ms": 1000600,
                    "finish_ms": 1001200  # Another 10 minutes
                },
                "readable": {
                    "start": "2026-04-18T05:05:54Z",
                    "finish": "2026-04-18T05:15:54Z",
                    "duration_ms": 600000
                }
            }
        ]

    @patch('prom_bench_stats.plotting.asyncio.run')
    @patch('prom_bench_stats.plotting.query_range')
    @patch('prom_bench_stats.plotting.matrix_to_per_series_charts')
    def test_complete_successful_workflow(self, mock_charts, mock_query, mock_asyncio):
        """Test complete successful workflow from dashboard to plots."""
        # Mock successful Prometheus responses
        mock_query.return_value = {
            "data": {"result": []}
        }
        
        # Mock chart data for each query
        mock_charts.return_value = [
            {
                "timestamps": [1000, 1010, 1020],
                "data": [1.0, 2.0, 3.0]
            }
        ]
        
        mock_asyncio.return_value = mock_query.return_value
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            dashboard_path = os.path.join(temp_dir, "grafana_dashboard.json")
            intervals_path = os.path.join(temp_dir, "test_intervals.json")
            output_dir = os.path.join(temp_dir, "plots")
            
            with open(dashboard_path, 'w') as f:
                json.dump(self.sample_dashboard, f)
            with open(intervals_path, 'w') as f:
                json.dump(self.sample_intervals, f)
            
            # Run the complete workflow
            process_grafana_dashboard(
                dashboard_path=dashboard_path,
                test_intervals_path=intervals_path,
                output_dir=output_dir,
                num_points=50
            )
            
            # Verify output
            assert os.path.exists(output_dir)
            
            # Check that plots were created for each panel/target
            plot_files = []
            for root, dirs, files in os.walk(output_dir):
                plot_files.extend([f for f in files if f.endswith('.png')])
            
            # Should have created plots for both panels
            assert len(plot_files) >= 2

    @patch('prom_bench_stats.plotting.asyncio.run')
    @patch('prom_bench_stats.plotting.query_range')
    @patch('prom_bench_stats.plotting.matrix_to_per_series_charts')
    def test_workflow_with_row_sections(self, mock_charts, mock_query, mock_asyncio):
        """Test workflow with row sections in dashboard."""
        dashboard_with_rows = {
            "dashboard": {
                "panels": [
                    {
                        "id": 1,
                        "title": "System Metrics",
                        "type": "row"
                    },
                    {
                        "id": 2,
                        "title": "CPU Usage",
                        "type": "graph",
                        "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
                        "targets": [
                            {"expr": "rate(process_cpu_seconds_total[5m])", "legendFormat": "CPU Rate"}
                        ]
                    },
                    {
                        "id": 3,
                        "title": "Application Metrics",
                        "type": "row"
                    },
                    {
                        "id": 4,
                        "title": "HTTP Requests",
                        "type": "graph",
                        "gridPos": {"x": 0, "y": 10, "w": 12, "h": 8},
                        "targets": [
                            {"expr": "rate(http_requests_total[5m])", "legendFormat": "Request Rate"}
                        ]
                    }
                ]
            }
        }
        
        # Mock successful responses
        mock_query.return_value = {"data": {"result": []}}
        mock_charts.return_value = [
            {
                "timestamps": [1000, 1010, 1020],
                "data": [1.0, 2.0, 3.0]
            }
        ]
        mock_asyncio.return_value = mock_query.return_value
        
        with tempfile.TemporaryDirectory() as temp_dir:
            dashboard_path = os.path.join(temp_dir, "dashboard.json")
            intervals_path = os.path.join(temp_dir, "intervals.json")
            output_dir = os.path.join(temp_dir, "plots")
            
            with open(dashboard_path, 'w') as f:
                json.dump(dashboard_with_rows, f)
            with open(intervals_path, 'w') as f:
                json.dump(self.sample_intervals, f)
            
            process_grafana_dashboard(
                dashboard_path=dashboard_path,
                test_intervals_path=intervals_path,
                output_dir=output_dir
            )
            
            # Should create section directories
            system_dir = os.path.join(output_dir, "system_metrics")
            app_dir = os.path.join(output_dir, "application_metrics")
            
            assert os.path.exists(system_dir)
            assert os.path.exists(app_dir)

    @patch('prom_bench_stats.plotting.asyncio.run')
    def test_workflow_with_partial_failures(self, mock_asyncio):
        """Test workflow with some fetch failures."""
        # Mock partial failures
        mock_asyncio.side_effect = [
            # First query succeeds
            {"data": {"result": []}},
            # Second query fails
            Exception("Prometheus timeout"),
            # Third query succeeds
            {"data": {"result": []}}
        ]
        
        dashboard_multiple_targets = {
            "dashboard": {
                "panels": [
                    {
                        "id": 1,
                        "title": "Multi Target Panel",
                        "type": "graph",
                        "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
                        "targets": [
                            {"expr": "up", "legendFormat": "Uptime"},
                            {"expr": "rate(http_requests_total[5m])", "legendFormat": "Request Rate"},
                            {"expr": "process_resident_memory_bytes", "legendFormat": "Memory"}
                        ]
                    }
                ]
            }
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            dashboard_path = os.path.join(temp_dir, "dashboard.json")
            intervals_path = os.path.join(temp_dir, "intervals.json")
            output_dir = os.path.join(temp_dir, "plots")
            
            with open(dashboard_path, 'w') as f:
                json.dump(dashboard_multiple_targets, f)
            with open(intervals_path, 'w') as f:
                json.dump(self.sample_intervals, f)
            
            with patch('prom_bench_stats.plotting.matrix_to_per_series_charts') as mock_charts:
                mock_charts.return_value = [
                    {
                        "timestamps": [1000, 1010, 1020],
                        "data": [1.0, 2.0, 3.0]
                    }
                ]
                
                process_grafana_dashboard(
                    dashboard_path=dashboard_path,
                    test_intervals_path=intervals_path,
                    output_dir=output_dir
                )
                
                # Should still create output directory
                assert os.path.exists(output_dir)

    @patch('prom_bench_stats.plotting.asyncio.run')
    @patch('prom_bench_stats.plotting.query_range')
    @patch('prom_bench_stats.plotting.matrix_to_per_series_charts')
    def test_main_function_integration(self, mock_charts, mock_query, mock_asyncio):
        """Test main function integration."""
        # Mock successful responses
        mock_query.return_value = {"data": {"result": []}}
        mock_charts.return_value = [
            {
                "timestamps": [1000, 1010, 1020],
                "data": [1.0, 2.0, 3.0]
            }
        ]
        mock_asyncio.return_value = mock_query.return_value
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            dashboard_file = os.path.join(temp_dir, "grafana_dashboard.json")
            intervals_file = os.path.join(temp_dir, "test_intervals.json")
            
            with open(dashboard_file, 'w') as f:
                json.dump(self.sample_dashboard, f)
            with open(intervals_file, 'w') as f:
                json.dump(self.sample_intervals, f)
            
            # Change to temp directory and run main
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                with patch('sys.argv', ['generate_plots.py']):
                    main()
                    
                    # Should create plots directory
                    plots_dir = os.path.join(temp_dir, "plots")
                    assert os.path.exists(plots_dir)
                    
            finally:
                os.chdir(original_cwd)

    def test_error_handling_integration(self):
        """Test error handling in integration scenarios."""
        # Test with completely invalid dashboard
        invalid_dashboard = {"invalid": "structure"}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            dashboard_path = os.path.join(temp_dir, "dashboard.json")
            intervals_path = os.path.join(temp_dir, "intervals.json")
            
            with open(dashboard_path, 'w') as f:
                json.dump(invalid_dashboard, f)
            with open(intervals_path, 'w') as f:
                json.dump(self.sample_intervals, f)
            
            # Should handle gracefully without crashing
            process_grafana_dashboard(
                dashboard_path=dashboard_path,
                test_intervals_path=intervals_path,
                output_dir=temp_dir
            )
            
            # Should still create output directory
            assert os.path.exists(temp_dir)

    @patch('prom_bench_stats.plotting.asyncio.run')
    @patch('prom_bench_stats.plotting.query_range')
    @patch('prom_bench_stats.plotting.matrix_to_per_series_charts')
    def test_empty_data_handling(self, mock_charts, mock_query, mock_asyncio):
        """Test handling of empty data responses."""
        # Mock empty data responses
        mock_query.return_value = {"data": {"result": []}}
        mock_charts.return_value = []  # Empty charts
        mock_asyncio.return_value = mock_query.return_value
        
        with tempfile.TemporaryDirectory() as temp_dir:
            dashboard_path = os.path.join(temp_dir, "dashboard.json")
            intervals_path = os.path.join(temp_dir, "intervals.json")
            output_dir = os.path.join(temp_dir, "plots")
            
            with open(dashboard_path, 'w') as f:
                json.dump(self.sample_dashboard, f)
            with open(intervals_path, 'w') as f:
                json.dump(self.sample_intervals, f)
            
            process_grafana_dashboard(
                dashboard_path=dashboard_path,
                test_intervals_path=intervals_path,
                output_dir=output_dir
            )
            
            # Should create output directory even with no data
            assert os.path.exists(output_dir)
            
            # Should not create any plot files
            plot_files = []
            for root, dirs, files in os.walk(output_dir):
                plot_files.extend([f for f in files if f.endswith('.png')])
            assert len(plot_files) == 0
