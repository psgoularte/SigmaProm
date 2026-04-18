"""Test suite for SigmaProm statistical analysis functionality."""

import asyncio
import json
import sys
import unittest
from unittest.mock import AsyncMock, patch

import pytest
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, '..')

from prom_bench_stats.statistical_analysis import (
    analyze_multiple_runs,
    calculate_optimal_interpolation_points,
    normalize_time_series_data,
    calculate_statistics,
    fetch_run_data
)


class TestStatisticalAnalysis(unittest.TestCase):
    """Test cases for statistical analysis functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.sample_dashboard = {
            "panels": [
                {
                    "id": 1,
                    "title": "Test Panel",
                    "targets": [
                        {"expr": "up", "legendFormat": "{{instance}}"},
                        {"expr": "rate(http_requests_total[5m])", "legendFormat": "Request Rate"}
                    ]
                }
            ]
        }
        
        self.sample_runs = [
            {
                "status": "success",
                "prometheus_timestamps": {
                    "start_ms": 1776488154750,
                    "finish_ms": 1776488291033
                },
                "readable": {
                    "start": "2026-04-18T04:55:54Z",
                    "finish": "2026-04-18T04:58:11Z",
                    "duration_ms": 136283
                }
            },
            {
                "status": "success",
                "prometheus_timestamps": {
                    "start_ms": 1776488291033,
                    "finish_ms": 1776488437854
                },
                "readable": {
                    "start": "2026-04-18T04:58:11Z",
                    "finish": "2026-04-18T05:00:37Z",
                    "duration_ms": 146821
                }
            }
        ]
    
    def test_calculate_optimal_interpolation_points_empty_data(self):
        """Test optimal points calculation with empty data."""
        result = calculate_optimal_interpolation_points([])
        self.assertEqual(result, 100)
    
    def test_calculate_optimal_interpolation_points_single_run(self):
        """Test optimal points calculation with single run."""
        runs_data = [
            {
                "timestamps": [1000, 1010, 1020],
                "values": [1, 2, 3]
            }
        ]
        result = calculate_optimal_interpolation_points(runs_data)
        self.assertTrue(50 <= result <= 300)
        self.assertEqual(result % 10, 0)  # Should be multiple of 10
    
    def test_calculate_optimal_interpolation_points_multiple_runs(self):
        """Test optimal points calculation with multiple runs."""
        runs_data = [
            {
                "timestamps": [1000, 1010, 1020],
                "values": [1, 2, 3]
            },
            {
                "timestamps": [1000, 1005, 1010, 1015, 1020],
                "values": [1.5, 2.5, 3.5, 4.5, 5.5]
            }
        ]
        result = calculate_optimal_interpolation_points(runs_data)
        self.assertTrue(50 <= result <= 300)
        self.assertEqual(result % 10, 0)
    
    def test_normalize_time_series_data_empty(self):
        """Test normalization with empty data."""
        result = normalize_time_series_data([], 100)
        self.assertTrue(result.empty)
    
    def test_normalize_time_series_data_invalid_points(self):
        """Test normalization with invalid points parameter."""
        runs_data = [
            {
                "timestamps": [1000, 1010, 1020],
                "values": [1, 2, 3]
            }
        ]
        result = normalize_time_series_data(runs_data, 0)
        self.assertTrue(result.empty)
    
    def test_normalize_time_series_data_valid(self):
        """Test normalization with valid data."""
        runs_data = [
            {
                "timestamps": [1000, 1010, 1020],
                "values": [1, 2, 3]
            }
        ]
        result = normalize_time_series_data(runs_data, 50)
        
        # Check structure
        self.assertIn('relative_time', result.columns)
        self.assertIn('value', result.columns)
        
        # Check data points
        self.assertEqual(len(result), 50)  # 50 points for 1 run
        self.assertTrue(all(0 <= t <= 1 for t in result['relative_time']))
    
    def test_calculate_statistics_empty(self):
        """Test statistics calculation with empty data."""
        result = calculate_statistics(pd.DataFrame())
        
        self.assertEqual(result['labels'], [])
        self.assertEqual(result['datasets'], [])
        self.assertEqual(result.get('sample_count', 0), 0)
        self.assertEqual(result.get('num_runs', 0), 0)
    
    def test_calculate_statistics_valid(self):
        """Test statistics calculation with valid data."""
        # Create test data with known statistics
        test_data = pd.DataFrame({
            'relative_time': [0.0, 0.5, 1.0],
            'value': [10.0, 20.0, 30.0],
            'run_id': [0, 1, 2]  # 3 different runs
        })
        
        result = calculate_statistics(test_data)
        
        # Check structure
        self.assertIn('labels', result)
        self.assertIn('datasets', result)
        self.assertIn('sample_count', result)
        self.assertIn('num_runs', result)
        
        # Check labels
        expected_labels = ['0%', '50%', '100%']
        self.assertEqual(result['labels'], expected_labels)
        
        # Check datasets
        self.assertEqual(len(result['datasets']), 3)  # mean, upper, lower
        self.assertEqual(result['sample_count'], 3)
        self.assertEqual(result['num_runs'], 1)
    
    def test_calculate_statistics_with_nan(self):
        """Test statistics calculation with NaN values."""
        # Create test data with NaN values
        test_data = pd.DataFrame({
            'relative_time': [0.0, 0.5, 1.0],
            'value': [1.0, np.nan, 3.0],
            'run_id': [0, 0, 0]
        })
        
        result = calculate_statistics(test_data)
        
        # Should handle NaN gracefully
        self.assertIn('labels', result)
        self.assertIn('datasets', result)
        self.assertEqual(len(result['datasets']), 3)  # mean, upper, lower
    
    @pytest.mark.asyncio
    async def test_analyze_multiple_runs_success(self):
        """Test successful analysis of multiple runs."""
        with patch('prom_bench_stats.statistical_analysis.fetch_run_data') as mock_fetch:
            # Mock successful data fetch
            mock_fetch.return_value = [
                {
                    "timestamps": [1000, 1010, 1020],
                    "values": [1, 2, 3]
                },
                {
                    "timestamps": [1000, 1005, 1010, 1015, 1020],
                    "values": [1.5, 2.5, 3.5, 4.5, 5.5]
                }
            ]
            
            result = await analyze_multiple_runs(
                dashboard=self.sample_dashboard,
                runs=self.sample_runs,
                step=None,
                num_points=100
            )
            
            # Check structure
            self.assertIn('panels', result)
            self.assertIn('total_runs', result)
            self.assertIn('num_points', result)
            self.assertIn('auto_detected', result)
            
            # Check values
            self.assertEqual(result['total_runs'], 2)
            self.assertEqual(result['num_points'], 100)
            self.assertFalse(result['auto_detected'])
            self.assertEqual(len(result['panels']), 1)
    
    @pytest.mark.asyncio
    async def test_analyze_multiple_runs_auto_detect(self):
        """Test analysis with auto-detection of points."""
        with patch('prom_bench_stats.statistical_analysis.fetch_run_data') as mock_fetch:
            mock_fetch.return_value = [
                {
                    "timestamps": [1000, 1010, 1020],
                    "values": [1, 2, 3]
                }
            ]
            
            result = await analyze_multiple_runs(
                dashboard=self.sample_dashboard,
                runs=self.sample_runs,
                step=None,
                num_points=None  # Auto-detect
            )
            
            # Check auto-detection
            self.assertTrue(result.get('auto_detected', False))
            self.assertTrue(50 <= result.get('num_points', 0) <= 300)
    
    @pytest.mark.asyncio
    async def test_analyze_multiple_runs_invalid_dashboard(self):
        """Test analysis with invalid dashboard."""
        with pytest.raises(ValueError, match="Invalid dashboard JSON"):
            await analyze_multiple_runs(
                dashboard={},
                runs=self.sample_runs,
                step=None,
                num_points=100
            )
    
    @pytest.mark.asyncio
    async def test_analyze_multiple_runs_no_valid_runs(self):
        """Test analysis with no valid runs."""
        with pytest.raises(ValueError, match="No panels with Prometheus targets found"):
            await analyze_multiple_runs(
                dashboard=self.sample_dashboard,
                runs=[{"status": "failed"}],  # No valid runs
                step=None,
                num_points=100
            )
    
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Test with None values in timestamps
        runs_data = [
            {
                "timestamps": [1000, None, 1020],
                "values": [1, None, 3]
            }
        ]
        
        # Should not crash and should handle gracefully
        result = calculate_optimal_interpolation_points(runs_data)
        self.assertTrue(50 <= result <= 300)


if __name__ == '__main__':
    unittest.main()
