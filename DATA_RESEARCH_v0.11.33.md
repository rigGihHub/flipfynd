# DATA RESEARCH v0.11.33 — Sold Comp Data Quality Audit

## Problem
FlipFynd already required explicit sold evidence during new imports, but some downstream paths still treated a numeric `sold_price` or a `market_state=sold` marker as realised-sale evidence. That meant legacy or externally altered rows could theoretically bypass the stricter import contract.

## Change
v0.11.33 introduces a single conservative sold-comp quality gate in `src/sold_comp_quality.py`.

A row may now influence realised-sale valuation only when it has all of:
- `sold_verification_status=verified`
- an approved explicit sale-evidence marker
- a positive realised sold price or sold total

Rows with sold-looking fields but without that verification metadata are retained in storage but blocked from valuation. The gate is also used when sold history is used to corroborate a visual identity or exact-comp candidate.

## Audit semantics
The UI reports:
- approved comps
- approved comps with stronger provenance/date metadata
- blocked legacy/incomplete sold rows
- grouped blocking reasons

No data is deleted or rewritten automatically.

## Safety principle
Active asking prices, ended listings without sale proof, legacy `sold_price` rows, and ambiguous `sold` status markers must never be silently promoted to verified realised-sale evidence.
