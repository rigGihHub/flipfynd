# FlipFynd v0.11.33 — Sold Comp Data Quality Audit

## Added
- New central `sold_comp_quality` gate.
- Sold Comp Data Quality Audit in the Smart Sold Comp Acquisition panel.
- Counts for approved, strong-metadata and blocked sold records.
- Explicit blocking reasons for legacy/incomplete records.

## Hardened
- Market valuation now rejects sold-looking rows that did not pass the strict verification pipeline.
- Exact Comp Hunter no longer treats an arbitrary `sold_price` or `market_state=sold` row as sold evidence.
- Visual identity corroboration can only be strengthened by verified sold evidence.
- Blocked records are not deleted; they simply cannot carry realised-sale valuation weight.

## Unchanged
- No automatic model reweighting.
- No new external sold-data source.
- No active listing is converted into a sold comp by inference.
- Existing valuation/ranking logic is unchanged except that unsafe sold evidence is now excluded.

## QA
- 393 tests passed.
- Python compileall passed.
- Release ZIP integrity checked.
- Live Streamlit deployment not verified for this release.
