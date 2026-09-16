# v0.14.31 — preserve risk through seller analysis

Debugging current main reproduced a false-positive path: the full-analysis
bridge dropped `risk_score`, so the final find gate substituted 50 even when
the underlying analysis reported 90. The seller UI also showed a green BUY
badge directly from the decision text when the final evidence gate rejected it.

- Preserve the original risk score and readiness in the full-analysis summary.
- Recover risk from source analysis for older compact/cached rows. When two
  scores conflict, use the higher risk; never silently substitute a passing score.
- Missing, nonnumeric, nonfinite, boolean and out-of-range risk evidence blocks
  an actionable find. The existing maximum permitted risk remains 65/100.
- Preliminary quick-analysis fallback cannot be presented as a verified find.
- Use final readiness for BUY labels and badges, and explain blockers. Rejected
  BUY candidates remain available for research; underlying decisions and values
  are preserved for inspection.

Validation: baseline 1,392 tests passed. All 17 initial risk regressions failed
before the fix. The final suite contains 25 new regression cases covering bridge
boundaries, cached summaries, missing/invalid risk, preliminary results, badge
evidence and the seller pipeline. Two existing verified-BUY fixtures now include
an explicit risk score. Full pytest suite: 1,417 passed. Entry points, source and
tests compile successfully.

No change to SOLD provenance, market values, comp matching or purchase economics.
This is a code-level correction; live Tradera searches and deployed Streamlit
behavior have not been verified by this test run.
