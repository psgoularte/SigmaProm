# prom-bench-stats

A small interface for loading Grafana dashboard JSON and rendering panels with Prometheus data via `query_range`.

## What this does

- imports Grafana dashboards (exported JSON)
- extracts Prometheus queries from panels
- runs `query_range` against Prometheus for each target
- displays raw series in Chart.js charts grouped by panel

## Graph behavior

The charts do not apply moving averages in the app or UI. They render the data returned by Prometheus via `query_range`, point by point.

If the Grafana query itself uses `avg_over_time`, `rate()`, `quantile_over_time()`, or other PromQL window functions, those values are already computed by Prometheus.

The app does not automatically rewrite Grafana JSON queries into instant queries.

## Requirements

- Python 3.9+
- Poetry
- Prometheus running and accessible

## Installation

```bash
poetry install
cp .env.example .env
```

Edit `.env` if Prometheus is not at `http://127.0.0.1:9090`.

## Configuration

In `.env`, set:

```env
PROMETHEUS_URL=http://127.0.0.1:9090
WEB_PORT=3030
```

## Running

```bash
poetry run prom-web
```

Open `http://127.0.0.1:3030` in your browser.

## How to use

1. Export the Grafana dashboard JSON (Share → JSON Model / Export JSON).
2. Paste the JSON into the page input.
3. Adjust the time window and step if needed.
4. Click `Render dashboard`.

## Useful endpoints

- `GET /api/health` — check the service
- `GET /api/diagnostics` — check Prometheus connectivity
- `POST /api/grafana/render-dashboard` — render the dashboard from JSON

## Tests

```bash
poetry run pytest
```

## Notes

The interface default time window is `5m`.
