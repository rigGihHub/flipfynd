# FlipFynd v0.11.68 – Validation Snapshot Integrity + Future Terminal UI

## Validation
- Flip Journal schema v6.
- Captures `net_profit_estimate` when explicit `net_profit` is absent.
- Captures expected resale through explicit known aliases only.
- Stores `prediction_timestamp_at_capture` at recommendation capture time.
- Captures sell-time only when evidence is exactly `verified_sold_velocity`.
- Stores velocity evidence at capture.
- Expected ROI now uses the actual captured expected-net-profit value.
- Historical rows are not backfilled or rewritten.

## UI
- Subtle futuristic trading-terminal treatment.
- Dark translucent panels, fine data-grid background and restrained amber glow.
- Decision hierarchy and existing information architecture remain unchanged.
- Mobile-safe styling; no neon-heavy cyberpunk redesign.
