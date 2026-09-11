# FlipFynd v0.12.35 – Streamlit Autopilot Compatibility Hotfix

- Live screenshot showed production still on v0.12.26 and crashing at `build_autopilot_plan(...)`.
- New `src/autopilot_compat.py` inspects the actually loaded planner signature before calling it.
- New planner gets `analyzed_results`; legacy planner is called without the unsupported keyword.
- This avoids relying on an exception path during Streamlit Cloud reload/deploy.
- No ranking, valuation, KÖP, market-fetch or collector-intelligence logic is changed.
- Version is bumped to v0.12.35 so deployment status is visible directly in the header.
