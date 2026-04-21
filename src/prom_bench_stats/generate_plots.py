#!/usr/bin/env python3
"""Generate matplotlib plots from Grafana dashboard and test intervals."""

import sys
import argparse
import shutil
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from prom_bench_stats.plotting import process_grafana_dashboard


def clean_plots_directory(plots_dir: Path) -> None:
    """Clean the plots directory by removing all files."""
    if plots_dir.exists():
        print(f"Cleaning plots directory: {plots_dir}")
        for file_path in plots_dir.glob("*.png"):
            file_path.unlink()
            print(f"Removed: {file_path}")
    else:
        plots_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created plots directory: {plots_dir}")


def main():
    """Main function to generate plots from any Grafana dashboard."""
    parser = argparse.ArgumentParser(
        description="Generate matplotlib plots from any Grafana dashboard and test intervals"
    )
    parser.add_argument(
        "dashboard",
        nargs='?',
        help="Path to Grafana dashboard JSON file (default: auto-detect in root)"
    )
    parser.add_argument(
        "intervals",
        nargs='?',
        help="Path to test intervals JSON file (default: auto-detect in root)"
    )
    parser.add_argument(
        "--output",
        default="plots",
        help="Output directory for generated plots (default: plots)"
    )
    parser.add_argument(
        "--interpol",
        type=int,
        default=100,
        help="Number of interpolation points for time series normalization (default: 100)"
    )
        
    args = parser.parse_args()
    
    # Auto-detect files if not provided
    project_root = Path(__file__).parent.parent.parent
    
    if args.dashboard:
        dashboard_path = Path(args.dashboard)
    else:
        # Auto-detect dashboard file
        dashboard_candidates = list(project_root.glob("*dashboard*.json"))
        if dashboard_candidates:
            dashboard_path = dashboard_candidates[0]
            print(f"Auto-detected dashboard: {dashboard_path}")
        else:
            print("Error: No dashboard file found in project root")
            print("Expected files like: grafana_dashboard.json, dashboard.json, etc.")
            sys.exit(1)
    
    if args.intervals:
        intervals_path = Path(args.intervals)
    else:
        # Auto-detect intervals file
        intervals_candidates = list(project_root.glob("*interval*.json"))
        if intervals_candidates:
            intervals_path = intervals_candidates[0]
            print(f"Auto-detected intervals: {intervals_path}")
        else:
            print("Error: No intervals file found in project root")
            print("Expected files like: test_intervals.json, intervals.json, etc.")
            sys.exit(1)
    
    output_dir = Path(args.output)
    
    if not dashboard_path.exists():
        print(f"Error: {dashboard_path} not found")
        sys.exit(1)
    
    if not intervals_path.exists():
        print(f"Error: {intervals_path} not found")
        sys.exit(1)
    
    # Clean plots directory
    clean_plots_directory(output_dir)
    
    # Generate plots
    print(f"Generating plots from Grafana dashboard: {dashboard_path}")
    print(f"Using test intervals: {intervals_path}")
    print(f"Output directory: {output_dir}")
    print(f"Using {args.interpol} interpolation points")
    print("Using automatic window sizing (2x sampling frequency)")
    
    process_grafana_dashboard(
        dashboard_path=str(dashboard_path),
        test_intervals_path=str(intervals_path),
        output_dir=str(output_dir),
        num_points=args.interpol
    )
    
    print(f"Plots generated successfully in '{output_dir}' directory!")


if __name__ == "__main__":
    main()
