cp .env.example .env

# Edit .env if Prometheus is not on 127.0.0.1:9090 — set PROMETHEUS_URL to your real URL.

poetry install
poetry run prom-web