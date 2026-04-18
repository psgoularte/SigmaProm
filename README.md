# SigmaProm

A comprehensive interface for analyzing Grafana dashboards with Prometheus data, including advanced statistical analysis of multiple benchmark runs.

## Features

### Real-time Dashboard
- **Dashboard import**: Load JSON exported from Grafana
- **Real-time rendering**: Display charts with raw Prometheus data via `query_range`
- **Responsive layout**: 24-column grid matching Grafana
- **Smart filtering**: Keeps constant charts (even if zero) for benchmarks

### Advanced Statistical Analysis
- **Multiple runs**: Process array of runs with timestamps
- **Temporal normalization**: Convert runs with different durations to relative timeline (0% to 100%)
- **Smart interpolation**: Ensures same number of points across runs
- **Robust statistics**: Calculate mean ± standard deviation point-by-point
- **Advanced visualization**: Shaded area showing confidence intervals
- **CSV export**: Individual download buttons for each chart data

## Chart Behavior

### Real-time
- Charts **do not apply moving averages** in the app or UI
- **Render raw data** returned by Prometheus via `query_range`, point by point
- If Grafana query uses `avg_over_time`, `rate()`, `quantile_over_time()`, or other PromQL window functions, these values are already computed by Prometheus

### Statistical Analysis
- **Normalization**: All runs are normalized to relative timeline
- **Interpolation**: Uses configurable number of points (default: 100)
- **Shaded area**: Visualizes mean ± standard deviation for noise analysis
- **Data export**: Individual "↓ CSV" buttons for downloading specific chart data
- **Consistent grid**: Maintains 24-col layout matching original dashboard

## Requirements

- Python 3.9+
- Poetry
- Prometheus running and accessible
- Pandas and NumPy (for statistical analysis)

## Installation

```bash
poetry install
cp .env.example .env
```

Edit `.env` if Prometheus is not at `http://127.0.0.1:9090`.

## Configuration

In `.env`, configure:

```env
PROMETHEUS_URL=http://127.0.0.1:9090
WEB_PORT=3030
```

## Usage

### Real-time Dashboard
1. **Export dashboard**: In Grafana: Share → JSON Model / Export JSON
2. **Paste JSON**: Paste in the main interface field
3. **Configure window**: Adjust time window (5m, 15m, 30m, 1h, 6h, 1d)
4. **Render**: Click "Render dashboard"

### Statistical Analysis
1. **Paste dashboard**: Use the same dashboard JSON as above
2. **Add runs**: Paste JSON array with benchmark executions:
   ```json
   [
     {
       "status": "success",
       "prometheus_timestamps": {
         "start_ms": 1704067200000,
         "finish_ms": 1704067260000
       }
     },
     {
       "status": "success", 
       "prometheus_timestamps": {
         "start_ms": 1704067320000,
         "finish_ms": 1704067380000
       }
     }
   ]
   ```
3. **Configure points**: Adjust number of interpolation points (10-500)
4. **Analyze**: Click "Analyze Runs"

## Useful Endpoints

### Health and Diagnostics
- `GET /api/health` — check service
- `GET /api/diagnostics` — check Prometheus connectivity

### Rendering
- `POST /api/grafana/render-dashboard` — render real-time dashboard
- `POST /api/grafana/statistical-analysis` — statistical analysis of multiple runs

## Tests

```bash
poetry run pytest
```

## Usage Tips

### For Benchmarks
- **Constant metrics**: Smart filter keeps important charts even with zero values
- **Relative windows**: Use 5m, 15m, 30m buttons for period analysis
- **Noise analysis**: Use statistical analysis to identify patterns between runs
- **Data export**: Use individual CSV buttons for detailed analysis

### For Monitoring
- **Real-time data**: Use dashboard for live monitoring
- **Historical analysis**: Use statistical analysis for trend analysis
- **Performance comparison**: Compare multiple benchmark runs statistically

## Architecture

- **Backend**: FastAPI with Prometheus client
- **Frontend**: Vanilla JavaScript with Chart.js
- **Statistical**: Pandas + NumPy for data processing
- **Export**: CSV download functionality for all chart data

## Development

```bash
# Install dependencies
poetry install
│   │   ├── dashboard.js   # Real-time dashboard
│   │   └── statistical.js # Statistical analysis
├── grafana_import.py      # Grafana dashboard parser
├── prometheus_fetch.py   # Prometheus client
├── statistical_analysis.py # Advanced statistical analysis
└── settings.py           # Configuration
```

### Technologies
- **Backend**: FastAPI, Python 3.9+
- **Frontend**: Chart.js, HTML5, CSS3
- **Processing**: Pandas, NumPy
- **Data**: Prometheus HTTP API
```

## License

MIT License - see LICENSE file for details.
