"""Configuration: point this app at the Prometheus started by your benchmark project."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from this package dir up to repo root (wherever .env exists).
_HERE = Path(__file__).resolve()
for _dir in _HERE.parents:
    _env = _dir / ".env"
    if _env.is_file():
        load_dotenv(_env)
        break
else:
    load_dotenv()


def prometheus_base_url() -> str:
    return os.environ.get("PROMETHEUS_URL", "http://127.0.0.1:9090").rstrip("/")
