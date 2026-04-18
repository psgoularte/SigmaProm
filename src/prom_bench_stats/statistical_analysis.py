"""Statistical analysis for multiple benchmark runs using Pandas."""

from __future__ import annotations

from typing import Any, List, Dict
import numpy as np
import pandas as pd

from prom_bench_stats.prometheus_fetch import query_range


def calculate_optimal_interpolation_points(runs_data: List[Dict[str, Any]]) -> int:
    """
    Calculate optimal number of interpolation points based on data characteristics.
    
    Args:
        runs_data: List of dictionaries containing timestamps and values for each run
        
    Returns:
        Optimal number of points for interpolation (between 50 and 300)
    """
    if not runs_data:
        return 100
    
    # Simple approach: use the maximum points from any run, but limit to reasonable range
    max_points_in_runs = 0
    
    for run_data in runs_data:
        values = run_data.get("values", [])
        if values:
            max_points_in_runs = max(max_points_in_runs, len(values))
    
    if max_points_in_runs == 0:
        return 100
    
    # Scale up slightly for smoother interpolation, but keep within bounds
    optimal_points = min(300, max(50, int(max_points_in_runs * 1.2)))
    
    # Round to nice numbers (multiples of 10)
    optimal_points = round(optimal_points / 10) * 10
    
    return optimal_points


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
        
        if not timestamps or not values:
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
            
        # Validate num_points
        if num_points is None or num_points <= 0:
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


def calculate_statistics(normalized_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate mean and standard deviation for normalized time series data.
    
    Args:
        normalized_df: DataFrame with normalized time series data
        
    Returns:
        Dictionary with statistics formatted for Chart.js
    """
    if normalized_df.empty:
        return {
            'labels': [],
            'datasets': []
        }
    
    # Group by relative_time and calculate statistics
    stats_df = normalized_df.groupby('relative_time')['value'].agg([
        'mean', 'std', 'count'
    ]).reset_index()
    
    # Handle cases where std is NaN (single values)
    stats_df['std'] = stats_df['std'].fillna(0)
    
    # Create labels (time as percentage)
    labels = [f"{int(t * 100)}%" for t in stats_df['relative_time']]
    
    # Create datasets for Chart.js with validation
    mean_values = []
    std_values = []
    
    for _, row in stats_df.iterrows():
        mean_val = row['mean']
        std_val = row['std']
        
        # Handle None and NaN values
        if mean_val is None or pd.isna(mean_val):
            mean_val = 0
        if std_val is None or pd.isna(std_val):
            std_val = 0
            
        mean_values.append(float(mean_val))
        std_values.append(float(std_val))
    
    # Upper and lower bounds (mean ± std)
    upper_values = [mean + std for mean, std in zip(mean_values, std_values)]
    lower_values = [mean - std for mean, std in zip(mean_values, std_values)]
    
    datasets = [
        {
            'label': 'Mean',
            'data': mean_values,
            'std_data': std_values,
            'upper_data': upper_values,
            'lower_data': lower_values,
            'borderColor': '#60a5fa',
            'backgroundColor': 'rgba(96, 165, 250, 0.1)',
            'fill': False,
            'tension': 0,
            'pointRadius': 2,
            'borderWidth': 2
        },
        {
            'label': 'Upper Bound (Mean + Std)',
            'data': upper_values,
            'std_data': std_values,
            'upper_data': upper_values,
            'lower_data': lower_values,
            'borderColor': 'rgba(96, 165, 250, 0.3)',
            'backgroundColor': 'rgba(96, 165, 250, 0.1)',
            'fill': '+1', # Fill to next dataset
            'tension': 0,
            'pointRadius': 0,
            'borderWidth': 1,
            'borderDash': [5, 5]
        },
        {
            'label': 'Lower Bound (Mean - Std)',
            'data': lower_values,
            'std_data': std_values,
            'upper_data': upper_values,
            'lower_data': lower_values,
            'borderColor': 'rgba(96, 165, 250, 0.3)',
            'backgroundColor': 'rgba(96, 165, 250, 0.1)',
            'fill': False,
            'tension': 0,
            'pointRadius': 0,
            'borderWidth': 1,
            'borderDash': [5, 5]
        }
    ]
    
    sample_count = int(stats_df['count'].iloc[0]) if not stats_df.empty and len(stats_df) > 0 else 0
    num_runs = int(normalized_df['run_id'].nunique()) if not normalized_df.empty and 'run_id' in normalized_df.columns else 0
    
    return {
        'labels': labels,
        'datasets': datasets,
        'sample_count': sample_count,
        'num_runs': num_runs
    }


async def fetch_run_data(
    query: str,
    runs: List[Dict[str, Any]],
    step: str | None = None
) -> List[Dict[str, Any]]:
    """
    Fetch Prometheus data for multiple runs.
    
    Args:
        query: PromQL query
        runs: List of run dictionaries with start_ms and finish_ms
        step: Step parameter for query_range
        
    Returns:
        List of dictionaries with timestamps and values for each run
    """
    runs_data = []
    
    for run in runs:
        if run.get('status') != 'success':
            continue
            
        timestamps = run.get('prometheus_timestamps', {})
        start_ms = timestamps.get('start_ms')
        finish_ms = timestamps.get('finish_ms')
        
        if not start_ms or not finish_ms:
            continue
            
        start_unix = start_ms / 1000.0
        finish_unix = finish_ms / 1000.0
        
        try:
            payload = await query_range(
                query=query,
                start_unix=start_unix,
                end_unix=finish_unix,
                step=step
            )
            
            data = payload.get('data', {})
            result = data.get('result', [])
            
            if not result:
                continue
                
            # Extract data from first series (for simplicity)
            series = result[0]
            values = series.get('values', [])
            
            if not values:
                continue
                
            timestamps_list = [float(pair[0]) for pair in values]
            values_list = [float(pair[1]) if pair[1] != 'NaN' else None for pair in values]
            
            runs_data.append({
                'timestamps': timestamps_list,
                'values': values_list
            })
            
        except Exception as e:
            # Log error but continue with other runs
            print(f"Error fetching data for run {start_ms}-{finish_ms}: {e}")
            continue
    
    return runs_data


async def analyze_multiple_runs(
    dashboard: Dict[str, Any],
    runs: List[Dict[str, Any]],
    step: str | None = None,
    num_points: int | None = None
) -> Dict[str, Any]:
    """
    Perform statistical analysis on multiple benchmark runs.
    
    Args:
        dashboard: Grafana dashboard JSON
        runs: List of run dictionaries with timestamps
        step: Step parameter for queries
        num_points: Number of points for interpolation
        
    Returns:
        Dictionary with statistical analysis results
    """
    from prom_bench_stats.grafana_import import get_dashboard_object, iter_grafana_panels
    
    dash = get_dashboard_object(dashboard)
    if not dash:
        raise ValueError("Invalid dashboard JSON")
    
    panels_spec = iter_grafana_panels(dash)
    if not panels_spec:
        raise ValueError("No panels with Prometheus targets found")
    
    results = []
    
    for panel in panels_spec:
        panel_results = []
        
        for target in panel.get('targets', []):
            expr = target.get('expr')
            if not expr:
                continue
                
            try:
                # Fetch data for all runs
                runs_data = await fetch_run_data(expr, runs, step)
                
                if not runs_data:
                    panel_results.append({
                        'expr': expr,
                        'legendFormat': target.get('legendFormat', ''),
                        'error': 'No data found for any run'
                    })
                    continue
                
                # Auto-detect optimal points if not specified
                if num_points is None:
                    optimal_points = calculate_optimal_interpolation_points(runs_data)
                else:
                    optimal_points = num_points
                
                # Normalize and calculate statistics
                normalized_df = normalize_time_series_data(runs_data, optimal_points)
                stats = calculate_statistics(normalized_df)
                
                panel_results.append({
                    'expr': expr,
                    'legendFormat': target.get('legendFormat', ''),
                    'statistics': stats,
                    'num_runs': len(runs_data)
                })
                
            except Exception as e:
                panel_results.append({
                    'expr': expr,
                    'legendFormat': target.get('legendFormat', ''),
                    'error': f'Analysis failed: {str(e)}'
                })
        
        if panel_results:
            results.append({
                'id': panel.get('id'),
                'title': panel.get('title', 'Panel'),
                'gridPos': panel.get('gridPos', {}),
                'targets': panel_results
            })
    
    return {
        'panels': results,
        'total_runs': len([r for r in runs if r.get('status') == 'success']),
        'num_points': optimal_points if 'optimal_points' in locals() else num_points or 100,
        'auto_detected': num_points is None
    }
