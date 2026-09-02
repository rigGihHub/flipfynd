# DATA RESEARCH v0.11.5

## Smart Refresh Scheduler

Refresh policy is intentionally heuristic and CPU-oriented, not market truth:
- pages 1-5: target refresh every 2 hours
- pages 6-20: every 8 hours
- pages 21-60: every 24 hours
- pages 61+: every 72 hours

The scheduler only chooses a small contiguous due block per sport. It does not alter card valuation, ranking, comps or buy recommendations.
