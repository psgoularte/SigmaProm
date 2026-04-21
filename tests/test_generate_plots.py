"""Tests for generate_plots module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from prom_bench_stats.generate_plots import clean_plots_directory, main


class TestCleanPlotsDirectory:
    """Test plots directory cleaning functionality."""

    def test_clean_existing_directory(self):
        """Test cleaning existing directory with files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some test files
            test_files = ['plot1.png', 'plot2.png', 'data.txt']
            for filename in test_files:
                Path(temp_dir) / filename
            
            # Only PNG files should be removed
            clean_plots_directory(Path(temp_dir))
            
            remaining_files = os.listdir(temp_dir)
            assert 'data.txt' in remaining_files
            assert 'plot1.png' not in remaining_files
            assert 'plot2.png' not in remaining_files

    def test_clean_nonexistent_directory(self):
        """Test cleaning non-existent directory creates it."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new_directory"
            
            clean_plots_directory(new_dir)
            
            assert new_dir.exists()
            assert new_dir.is_dir()


class TestMainFunction:
    """Test main function functionality."""

    def test_auto_detect_files(self):
        """Test auto-detection of dashboard and intervals files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            dashboard_file = Path(temp_dir) / "grafana_dashboard.json"
            intervals_file = Path(temp_dir) / "test_intervals.json"
            
            dashboard_file.write_text('{"panels": []}')
            intervals_file.write_text('[]')
            
            with patch('sys.argv', ['generate_plots.py']):
                with patch('prom_bench_stats.generate_plots.process_grafana_dashboard') as mock_process:
                    main()
                    
                    # Should call process_grafana_dashboard with auto-detected files
                    mock_process.assert_called_once()
                    args = mock_process.call_args[1]
                    assert args['dashboard_path'] == str(dashboard_file)
                    assert args['test_intervals_path'] == str(intervals_file)

    def test_no_dashboard_file(self):
        """Test behavior when no dashboard file is found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('sys.argv', ['generate_plots.py']):
                with patch('sys.exit') as mock_exit:
                    main()
                    mock_exit.assert_called_once_with(1)

    def test_no_intervals_file(self):
        """Test behavior when no intervals file is found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create only dashboard file
            dashboard_file = Path(temp_dir) / "grafana_dashboard.json"
            dashboard_file.write_text('{"panels": []}')
            
            with patch('sys.argv', ['generate_plots.py']):
                with patch('sys.exit') as mock_exit:
                    main()
                    mock_exit.assert_called_once_with(1)

    def test_custom_arguments(self):
        """Test with custom dashboard and intervals arguments."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dashboard_file = Path(temp_dir) / "custom_dashboard.json"
            intervals_file = Path(temp_dir) / "custom_intervals.json"
            
            dashboard_file.write_text('{"panels": []}')
            intervals_file.write_text('[]')
            
            with patch('sys.argv', [
                'generate_plots.py',
                str(dashboard_file),
                str(intervals_file),
                '--output', 'custom_output',
                '--interpol', '150'
            ]):
                with patch('prom_bench_stats.generate_plots.process_grafana_dashboard') as mock_process:
                    main()
                    
                    args = mock_process.call_args[1]
                    assert args['output_dir'] == 'custom_output'
                    assert args['num_points'] == 150

    def test_nonexistent_custom_files(self):
        """Test with custom file paths that don't exist."""
        with patch('sys.argv', [
            'generate_plots.py',
            '/nonexistent/dashboard.json',
            '/nonexistent/intervals.json'
        ]):
            with patch('sys.exit') as mock_exit:
                main()
                mock_exit.assert_called_once_with(1)
