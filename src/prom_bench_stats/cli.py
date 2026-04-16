"""Run the web server (uvicorn)."""

from __future__ import annotations


def main() -> None:
    from prom_bench_stats.settings import web_port

    import uvicorn

    uvicorn.run(
        "prom_bench_stats.web:app",
        host="0.0.0.0",
        port=web_port(),
        reload=False,
    )


if __name__ == "__main__":
    main()
