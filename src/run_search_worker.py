"""Worker bootstrap for persistent ordinary searches.

Deployment command:
    python -m src.run_search_worker

The actual analysis callable is resolved from the shared engine only; this
module never imports app.py or Streamlit.
"""
from __future__ import annotations

from src.search_job_worker import worker_loop
from src.ordinary_search_worker import execute_ordinary_search_job


def _handler(payload, progress):
    # The full shared analyze_data implementation is attached here once the
    # orchestration extraction is complete. Fail closed rather than silently
    # running a different ranking path.
    from src.ordinary_analysis_pipeline import analyze_data
    return execute_ordinary_search_job(payload, progress, analyze_fn=analyze_data)


def main():
    worker_loop(_handler)


if __name__ == "__main__":
    main()
