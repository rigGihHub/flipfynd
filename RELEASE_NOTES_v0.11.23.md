# FlipFynd v0.11.23 – Adaptive Candidate Deepening

- Replaces the rigid top-12-only full-analysis gate with adaptive deepening.
- Always preserves the old top-12 baseline.
- Adds full analysis for candidates close to the fast-score cutoff or carrying independent scarcity/demand/review signals.
- Hard cap of 30 full-analysis candidates protects interactive performance.
- Adaptive selection changes analysis coverage only; it does not create value, profit, max bid, or alter final ranking by itself.
- Adds diagnostics for selected full analyses and extra adaptive analyses.
