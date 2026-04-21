"""Generate matplotlib plots for mean and standard deviation from raw data."""

from __future__ import annotations

from typing import Any, List, Dict
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone


def load_json_data(file_path: str) -> Dict[str, Any]:
    """Load JSON data from file."""
    with open(file_path, 'r') as f:
        return json.load(f)


def calculate_sampling_frequency(timestamps: List[float]) -> float:
    """
    Calculate the sampling frequency from timestamps.
    
    Args:
        timestamps: List of Unix timestamps
        
    Returns:
        Average sampling interval in seconds
    """
    if len(timestamps) < 2:
        return 1.0  # Default to 1 second if insufficient data
    
    # Sort timestamps to ensure proper order
    sorted_timestamps = sorted(timestamps)
    
    # Calculate intervals between consecutive timestamps
    intervals = []
    for i in range(1, len(sorted_timestamps)):
        interval = sorted_timestamps[i] - sorted_timestamps[i-1]
        if interval > 0:  # Only consider positive intervals
            intervals.append(interval)
    
    if not intervals:
        return 1.0  # Default if no valid intervals found
    
    # Return the mean interval
    mean_interval = sum(intervals) / len(intervals)
    
    return float(mean_interval)


def calculate_optimal_window_size(timestamps: List[float]) -> float:
    """
    Calculate optimal window size as double the sampling frequency.
    
    Args:
        timestamps: List of Unix timestamps
        
    Returns:
        Window size in seconds (2x sampling interval)
    """
    sampling_interval = calculate_sampling_frequency(timestamps)
    window_size = sampling_interval * 2
    
    # Ensure minimum window size of 1 second
    return max(window_size, 1.0)


def calculate_windowed_averages(
    timestamps: List[float], 
    values: List[float], 
    window_seconds: int = 5
) -> tuple[List[datetime], List[float]]:
    """
    Calculate windowed averages for time series data.
    
    Args:
        timestamps: List of Unix timestamps
        values: List of corresponding values
        window_seconds: Window size in seconds for averaging
        
    Returns:
        Tuple of (window_centers_datetime, averaged_values)
    """
    if not timestamps or not values or len(timestamps) != len(values):
        return [], []
    
    # Convert to pandas DataFrame for easier manipulation
    df = pd.DataFrame({
        'timestamp': timestamps,
        'value': values
    })
    
    # Remove NaN values
    df = df.dropna(subset=['value'])
    
    if len(df) < 2:
        return [], []
    
    # Sort by timestamp
    df = df.sort_values('timestamp')
    
    # Calculate window boundaries
    start_time = df['timestamp'].min()
    end_time = df['timestamp'].max()
    
    window_centers = []
    window_averages = []
    
    # Slide window in steps of window_seconds
    current_start = start_time
    while current_start < end_time:
        current_end = min(current_start + window_seconds, end_time)
        window_center = current_start + (current_end - current_start) / 2
        
        # Get data within current window
        window_data = df[(df['timestamp'] >= current_start) & 
                        (df['timestamp'] < current_end)]
        
        if not window_data.empty:
            # Calculate average for this window
            window_avg = window_data['value'].mean()
            window_centers.append(datetime.fromtimestamp(window_center, tz=timezone.utc))
            window_averages.append(window_avg)
        
        current_start = current_start + window_seconds
    
    return window_centers, window_averages


def create_windowed_plot(
    timestamps: List[float], 
    values: List[float],
    title: str = "Time Series with Windowed Averages",
    output_path: str = "windowed_plot.png",
    window_seconds: int = None
) -> None:
    """
    Create a plot with windowed averages for single interval data.
    
    Args:
        timestamps: List of Unix timestamps
        values: List of corresponding values
        title: Plot title
        output_path: Path to save the PNG file
        window_seconds: Window size in seconds for averaging (if None, auto-calculated)
    """
    if not timestamps or not values:
        print("No data provided for plotting")
        return
    
    # Calculate optimal window size if not provided
    if window_seconds is None:
        window_seconds = calculate_optimal_window_size(timestamps)
        # Format to show clean numbers (max 2 decimal places)
        formatted_window = f"{window_seconds:.2f}".rstrip('0').rstrip('.')
        print(f"Auto-calculated window size: {formatted_window} seconds")
    else:
        print(f"Using specified window size: {window_seconds} seconds")
    
    # Calculate windowed averages
    window_centers, window_averages = calculate_windowed_averages(
        timestamps, values, window_seconds
    )
    
    if not window_centers:
        print("No valid windowed data for plotting")
        return
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    
    # Plot original data points (sampled to avoid overcrowding)
    sample_rate = max(1, len(timestamps) // 1000)  # Sample if too many points
    sample_timestamps = [datetime.fromtimestamp(ts, tz=timezone.utc) 
                        for i, ts in enumerate(timestamps) if i % sample_rate == 0]
    sample_values = [values[i] for i in range(len(values)) if i % sample_rate == 0]
    
    plt.scatter(sample_timestamps, sample_values, alpha=0.3, s=1, color='gray'  )
    
    # Format window size for clean display in legend (max 2 decimal places)
    formatted_window = f"{window_seconds:.2f}".rstrip('0').rstrip('.')
    
    # Plot windowed averages
    plt.plot(window_centers, window_averages, 'b-', linewidth=2, 
             label=f'{formatted_window}s Window Average')
    
    plt.xlabel('Time')
    plt.ylabel('Value')
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Format x-axis for better readability
    plt.gcf().autofmt_xdate()
    
    # Create output directory if it doesn't exist
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save the plot
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Windowed plot saved to: {output_path}")


def create_mean_std_plot(
    runs_data: List[Dict[str, Any]], 
    title: str = "Benchmark Statistics",
    output_path: str = "benchmark_stats.png",
    num_points: int = 100
) -> None:
    """
    Create matplotlib plot showing mean and standard deviation.
    
    Args:
        runs_data: List of dictionaries containing timestamps and values for each run
        title: Plot title
        output_path: Path to save the PNG file
        num_points: Number of interpolation points for time series normalization
    """
    if not runs_data:
        print("No data provided for plotting")
        return
    
    # Normalize time series data
    normalized_df = normalize_time_series_data(runs_data, num_points=num_points)
    
    if normalized_df.empty:
        print("No valid data for plotting")
        return
    
    # Calculate statistics
    stats_df = normalized_df.groupby('relative_time')['value'].agg([
        'mean', 'std', 'count'
    ]).reset_index()
    
    # Handle cases where std is NaN (single values)
    stats_df['std'] = stats_df['std'].fillna(0)
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    
    # Time as percentage
    time_percentages = stats_df['relative_time'] * 100
    mean_values = stats_df['mean']
    std_values = stats_df['std']
    
    # Upper and lower bounds
    upper_values = mean_values + std_values
    lower_values = mean_values - std_values
    
    # Plot mean line
    plt.plot(time_percentages, mean_values, 'b-', linewidth=2, label='Mean')
    
    # Fill the area between mean ± std
    plt.fill_between(time_percentages, lower_values, upper_values, 
                     alpha=0.3, color='blue', label='Mean ± Std')
    
    # Plot the bounds as dashed lines
    plt.plot(time_percentages, upper_values, 'b--', alpha=0.5, linewidth=1)
    plt.plot(time_percentages, lower_values, 'b--', alpha=0.5, linewidth=1)
    
    plt.xlabel('Time Progress (%)')
    plt.ylabel('Value')
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Create output directory if it doesn't exist
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save the plot
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Plot saved to: {output_path}")


def normalize_time_series_data(
    runs_data: List[Dict[str, Any]], 
    num_points: int = 100
) -> pd.DataFrame:
    """
    Normalize multiple time series runs to a common time axis.
    
    Args:
        runs_data: List of dictionaries containing timestamps and values for each run
        num_points: Number of points to interpolate to
        
    Returns:
        DataFrame with normalized time series (0.0 to 1.0) and interpolated values
    """
    if not runs_data:
        return pd.DataFrame()
    
    normalized_runs = []
    
    for run_data in runs_data:
        timestamps = run_data.get("timestamps", [])
        values = run_data.get("values", [])
        
        if len(timestamps) == 0 or len(values) == 0:
            continue
            
        # Convert to relative time (0.0 to 1.0)
        start_time = timestamps[0]
        end_time = timestamps[-1]
        duration = end_time - start_time
        
        if duration <= 0:
            continue
            
        relative_times = [(ts - start_time) / duration for ts in timestamps]
        
        # Create DataFrame for this run
        df_run = pd.DataFrame({
            'relative_time': relative_times,
            'value': values
        })
        
        # Remove NaN values
        df_run = df_run.dropna(subset=['value'])
        
        if len(df_run) < 2:
            continue
            
        # Interpolate to standard number of points
        new_times = np.linspace(0, 1, num_points)
        df_interpolated = pd.DataFrame({'relative_time': new_times})
        
        # Interpolate values with error handling
        try:
            df_interpolated['value'] = np.interp(
                new_times, 
                df_run['relative_time'], 
                df_run['value']
            )
        except (TypeError, ValueError) as e:
            print(f"Interpolation error for run: {e}")
            continue
        
        normalized_runs.append(df_interpolated)
    
    if not normalized_runs:
        return pd.DataFrame()
    
    # Combine all runs
    combined_df = pd.concat(normalized_runs, ignore_index=True)
    combined_df['run_id'] = combined_df.groupby(level=0).cumcount() // num_points
    
    return combined_df


def process_grafana_dashboard(
    dashboard_path: str, 
    test_intervals_path: str,
    output_dir: str = "plots",
    num_points: int = 100
) -> None:
    """
    Process any Grafana dashboard and test intervals to generate plots.
    
    Args:
        dashboard_path: Path to any Grafana dashboard JSON
        test_intervals_path: Path to test intervals JSON
        output_dir: Directory to save plots
        num_points: Number of interpolation points for time series normalization
        
    This function is generic and works with any Grafana dashboard structure.
    For single intervals, uses automatic windowed averaging (2x sampling frequency).
    For multiple intervals, uses statistical analysis.
    """
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Track failed fetches for final warning
    failed_fetches = []
    
    # Load data
    dashboard = load_json_data(dashboard_path)
    test_intervals = load_json_data(test_intervals_path)
    
    # Check if single or multiple intervals
    is_single_interval = len(test_intervals) == 1
    if is_single_interval:
        print("Single interval detected, using automatic windowed averaging (2x sampling frequency)")
    else:
        print(f"Multiple intervals detected ({len(test_intervals)}), using statistical analysis")
    
    # Extract panels and queries from dashboard
    from prom_bench_stats.grafana_import import get_dashboard_object, iter_grafana_panels_with_sections
    
    dash = get_dashboard_object(dashboard)
    if not dash:
        print("Invalid dashboard JSON")
        return
    
    panels_spec = iter_grafana_panels_with_sections(dash)
    if not panels_spec:
        print("No panels with Prometheus targets found")
        return
    
    # Process each panel
    for panel in panels_spec:
        panel_title = panel.get('title', 'Panel')
        panel_type = panel.get('type', 'timeseries')
        current_section = panel.get('section', 'general')
        
        # Create section directory if this is a row panel
        if panel_type == 'row':
            section_dir = Path(output_dir) / current_section
            section_dir.mkdir(exist_ok=True)
            print(f"Created section: {current_section}")
            continue
        
        for target in panel.get('targets', []):
            expr = target.get('expr')
            if not expr:
                continue
            
            legend_format = target.get('legendFormat', expr)
            
            # Fetch data from Prometheus for each test interval
            print(f"Processing panel: {panel_title} - {legend_format}")
            
            # Fetch actual Prometheus data
            runs_data = []
            for interval in test_intervals:
                start_time = interval.get('prometheus_timestamps', {}).get('start_ms') / 1000
                end_time = interval.get('prometheus_timestamps', {}).get('finish_ms') / 1000
                
                if not start_time or not end_time:
                    continue
                    
                try:
                    # Import here to avoid circular imports
                    from prom_bench_stats.prometheus_fetch import query_range, matrix_to_per_series_charts
                    import asyncio
                    
                    # Fetch data from Prometheus
                    result = asyncio.run(query_range(
                        query=expr,
                        start_unix=start_time,
                        end_unix=end_time
                    ))
                    
                    # Convert to chart format
                    charts = matrix_to_per_series_charts(result.get('data', {}).get('result', []))
                    
                    for chart in charts:
                        runs_data.append({
                            'timestamps': chart['timestamps'],
                            'values': chart['data']
                        })
                        
                except Exception as e:
                    error_msg = f"Error fetching data for interval {start_time}-{end_time}: {e}"
                    print(error_msg)
                    failed_fetches.append({
                        'panel': panel_title,
                        'legend': legend_format,
                        'query': expr,
                        'interval': f"{start_time}-{end_time}",
                        'error': str(e)
                    })
                    continue
            
            if runs_data:
                # Create section directory if it doesn't exist
                section_dir = Path(output_dir) / current_section
                section_dir.mkdir(exist_ok=True)
                
                # Make filename safe for any operating system
                safe_panel_title = (
                    panel_title.lower()
                    .replace(' ', '_')
                    .replace('(', '')
                    .replace(')', '')
                    .replace('/', '_')
                    .replace('\\', '_')
                    .replace(':', '_')
                    .replace('*', '_')
                    .replace('?', '_')
                    .replace('"', '_')
                    .replace('<', '_')
                    .replace('>', '_')
                    .replace('|', '_')
                    .replace('__', '_')
                    .strip('_')
                )
                safe_legend = (
                    legend_format.lower()
                    .replace(' ', '_')
                    .replace('(', '')
                    .replace(')', '')
                    .replace('/', '_')
                    .replace('\\', '_')
                    .replace(':', '_')
                    .replace('*', '_')
                    .replace('?', '_')
                    .replace('"', '_')
                    .replace('<', '_')
                    .replace('>', '_')
                    .replace('|', '_')
                    .replace('__', '_')
                    .strip('_')
                )
                output_path = section_dir / f"{safe_panel_title}_{safe_legend}.png"
                
                # Choose plotting method based on number of intervals
                if is_single_interval:
                    # For single interval, use windowed averaging
                    # Use the first (and only) series data
                    first_series = runs_data[0]
                    create_windowed_plot(
                        timestamps=first_series['timestamps'],
                        values=first_series['values'],
                        title=f"{panel_title} - {legend_format}",
                        output_path=str(output_path),
                        window_seconds=None  # Auto-calculate
                    )
                else:
                    # For multiple intervals, use statistical analysis
                    create_mean_std_plot(
                        runs_data=runs_data,
                        title=f"{panel_title} - {legend_format}",
                        output_path=str(output_path),
                        num_points=num_points
                    )
            else:
                no_data_msg = f"No data fetched for panel: {panel_title} - {legend_format}"
                print(no_data_msg)
                failed_fetches.append({
                    'panel': panel_title,
                    'legend': legend_format,
                    'query': expr,
                    'interval': 'all intervals',
                    'error': 'No data returned'
                })
    
    # Final warning summary
    if failed_fetches:
        print("\n" + "="*80)
        print("WARNING: Summary of failed data fetches")
        print("="*80)
        print(f"Total failures: {len(failed_fetches)}")
        print("\nPanels/queries that could not be processed:")
        
        # Group by panel for better readability
        panels_with_errors = {}
        for failure in failed_fetches:
            panel_key = failure['panel']
            if panel_key not in panels_with_errors:
                panels_with_errors[panel_key] = []
            panels_with_errors[panel_key].append(failure)
        
        for panel, errors in panels_with_errors.items():
            print(f"\nPanel: {panel}")
            for error in errors:
                print(f"  • Query: {error['legend']}")
                print(f"    Interval: {error['interval']}")
                print(f"    Error: {error['error']}")
        
    else:
        print("\n✅ All data was successfully fetched!")




if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python plotting.py <grafana_dashboard.json> <test_intervals.json>")
        sys.exit(1)
    
    dashboard_path = sys.argv[1]
    test_intervals_path = sys.argv[2]
    
    process_grafana_dashboard(dashboard_path, test_intervals_path)
