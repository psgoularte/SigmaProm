# Prom Bench Stats

A generic matplotlib-based tool for generating statistical plots from **any** Grafana dashboard and Prometheus data. Features intelligent plotting modes: statistical analysis for multiple benchmark runs and windowed averaging for single intervals.

## Features

- **Generic Dashboard Support**: Works with any Grafana dashboard JSON structure
- **Dynamic Section Organization**: Automatically creates folders based on dashboard rows
- **Statistical Analysis**: Generate mean and standard deviation plots from multiple benchmark runs
- **Windowed Averaging**: Automatic windowed averaging for single intervals (2x sampling frequency)
- **Intelligent Mode Detection**: Automatically switches between statistical and windowed modes
- **Matplotlib Integration**: High-quality PNG output with datetime x-axis
- **Smart Window Sizing**: Calculates optimal window size based on data sampling frequency
- **Clean Number Formatting**: Professional display with automatic decimal optimization
- **Multiple Run Processing**: Analyze multiple benchmark runs with temporal normalization
- **Smart Interpolation**: Normalize runs with different durations to relative timeline
- **Universal Filename Handling**: Safe filename generation for any operating system

## Installation

```bash
poetry install
```

## Usage

### Generate Plots (Automatic Detection)

The tool automatically detects dashboard and intervals files in the project root and intelligently chooses the appropriate plotting mode:

```bash
# Simple usage - auto-detects files and mode
poetry run python src/prom_bench_stats/generate_plots.py

# Custom interpolation points (for multiple intervals)
poetry run python src/prom_bench_stats/generate_plots.py --interpol 200

# Custom output directory
poetry run python src/prom_bench_stats/generate_plots.py --output my_plots

# Full example with custom settings
poetry run python src/prom_bench_stats/generate_plots.py --output results --interpol 150
```

### Manual File Specification

You can also specify files explicitly:

```bash
poetry run python src/prom_bench_stats/generate_plots.py <dashboard.json> <intervals.json>
```

**Command Line Options:**
- `dashboard`: Path to Grafana dashboard JSON file (optional - auto-detected)
- `intervals`: Path to test intervals JSON file (optional - auto-detected)
- `--output`: Output directory for generated plots (default: plots)
- `--interpol`: Number of interpolation points for time series normalization (default: 100)
  - Lower values (50-100): Faster processing, smoother curves
  - Higher values (150-300): More detail, better for complex patterns

### Intelligent Plotting Modes

The tool automatically detects the number of intervals and chooses the appropriate mode:

**Single Interval Mode** (1 interval):
- Automatic windowed averaging with window size = 2x sampling frequency
- Clean datetime x-axis formatting
- Professional number display (max 2 decimal places)
- Example output: `Auto-calculated window size: 12.22 seconds`

**Multiple Intervals Mode** (2+ intervals):
- Statistical analysis with mean ± standard deviation
- Relative time axis (0-100%)
- Traditional benchmark comparison plots

### Windowed Averaging Details

For single intervals, the system:
1. **Analyzes sampling frequency** from your data timestamps
2. **Calculates optimal window size** as 2x the sampling interval
3. **Applies fixed-window averaging** (not moving average)
4. **Formats numbers professionally** with automatic decimal optimization

Example window sizes based on data:
- 1s sampling frequency: 2s window
- 5s sampling frequency: 10s window  
- 0.5s sampling frequency: 1s window

### Auto-Detection

The tool automatically finds files in project root using these patterns:
- **Dashboard**: `*dashboard*.json` (grafana_dashboard.json, dashboard.json, etc.)
- **Intervals**: `*interval*.json` (test_intervals.json, intervals.json, etc.)

**Note**: `prometheus.yml` is only needed for running Prometheus server, not for plot generation.

### Required Files

The tool works with any two JSON files:

1. **Any Grafana Dashboard JSON** - Exported from any Grafana instance
2. **Test Intervals JSON** - Test interval data with timestamps

Example `test_intervals.json`:
```json
[
  {
    "status": "success",
    "prometheus_timestamps": {
      "start_ms": 1704067200000,
      "finish_ms": 1704070800000
    },
    "readable": {
      "start": "2024-01-01T00:00:00Z",
      "finish": "2024-01-01T02:00:00Z",
      "duration_ms": 7200000
    }
  }
]
```

## Output

Generated plots are saved as PNG files organized by dashboard sections with intelligent mode-based formatting:

### Single Interval Output (Windowed Averaging)
- **Datetime X-axis**: Real timestamps with automatic formatting
- **Windowed Average Line**: Clean line showing averaged values
- **Original Data Points**: Sampled raw data points in gray
- **Professional Legend**: Shows window size (e.g., "12.22s Window Average")
- **Clean Number Formatting**: Maximum 2 decimal places, removes trailing zeros

### Multiple Intervals Output (Statistical Analysis)
- **Relative Time X-axis**: 0-100% timeline for run comparison
- **Mean Line**: Central tendency across all runs
- **Standard Deviation Band**: Shaded area showing variability
- **Upper/Lower Bounds**: Dashed lines for mean ± std

### Output Structure
```
plots/
|-- section_1/                    # Based on dashboard rows
|   |-- metric_1_legend.png       # Windowed or statistical plot
|   |-- metric_2_legend.png
|-- section_2/
|   |-- metric_3_legend.png
`-- general/                      # Panels without sections
    |-- metric_4_legend.png
```

### Plot Features
- **Dynamic Folder Structure**: Creates folders based on Grafana dashboard rows
- **Universal Filenames**: Safe names for any operating system
- **High-resolution Output**: 300 DPI suitable for reports
- **Automatic Mode Selection**: Intelligently chooses plotting method
- **Professional Formatting**: Clean, publication-ready visualizations

## Architecture

- **Generic Plotting**: `src/prom_bench_stats/plotting.py` - Universal matplotlib functionality with intelligent mode selection
- **Dashboard Parser**: `src/prom_bench_stats/grafana_import.py` - Works with any Grafana JSON
- **Prometheus Integration**: `src/prom_bench_stats/prometheus_fetch.py` - Data fetching
- **Statistical Analysis**: Built-in interpolation and normalization
- **Windowed Averaging**: Automatic frequency detection and optimal window sizing
- **Smart Formatting**: Professional number display and datetime handling
- **Dependencies**: pandas, numpy, matplotlib, httpx

## Project Structure

```
prom-bench-stats/
├── src/
│   └── prom_bench_stats/
│       ├── generate_plots.py     # Generic main script
│       ├── plotting.py           # Universal matplotlib plotting
│       ├── grafana_import.py     # Any-dashboard JSON parser
│       ├── prometheus_fetch.py  # Prometheus data fetching
│       └── settings.py          # Configuration
├── grafana_dashboard.json      # Grafana dashboard
├── test_intervals.json        # Test interval data
├── plots/                    # Generated plots (auto-organized)
├── .env                      # Prometheus URL configuration
├── .env.example              # Environment template
└── pyproject.toml           # Dependencies
```

## Clean Project

The project has been cleaned to include only essential files:
- ✅ Removed: `docker-compose.yml`, `prometheus.yml` (not needed for plotting)
- ✅ Removed: `.pytest_cache/`, `.venv/` (development artifacts)
- ✅ Kept: Core source code, configuration, and generated plots

## Key Improvements for Generic Usage

1. **Intelligent Mode Selection**: Automatically switches between windowed averaging and statistical analysis
2. **No Hardcoded Assumptions**: Works with any Grafana dashboard structure
3. **Dynamic Section Creation**: Folders created based on actual dashboard rows
4. **Universal Character Handling**: Safe filenames for any language/special characters
5. **Flexible Arguments**: Accept any dashboard and intervals files
6. **Cross-Platform Compatible**: Safe filename generation for Windows/Linux/macOS
7. **Smart Window Sizing**: Automatically calculates optimal window size from data frequency
8. **Professional Formatting**: Clean number display with automatic decimal optimization

## Dependencies

- **pandas** >= 2.0.0
- **numpy** >= 1.24.0  
- **matplotlib** >= 3.5.0

## License

MIT License - see LICENSE file for details.
