# v0.14.34 — latest listings first, one refresh action

- One primary refresh button and a shared Hockey / Football / Both selector.
  Removed duplicate per-sport, autopilot and administration refresh buttons.
  Broader archive fetches remain under one collapsed advanced choice.
- The default fetch explicitly requests Tradera's AddedOn (Senast inlagda)
  order, reads at most three result pages per sport, and stops after two
  consecutive pages of known listings. It skips detail-page enrichment.
  This bounds work; it does not claim complete coverage or a fixed runtime.
- Merge each page into the saved archive. Update known listings and preserve
  their existing shipping, seller and enriched details when absent on the page.
  A scan timestamp records discovery, not the listing's publication date.
- Ordinary analysis defaults to the most recent latest-first snapshot per
  sport. The advanced filter can include older saved listings; legacy datasets
  still work before the first quick refresh. Older listings remain available
  as comparison context within the existing analysis limits.
- Latest-first pages do not advance or repair the separate archive checkpoint.
  Archive refreshes preserve latest-snapshot membership. Fixed an existing
  local-import scope error in the broader market-batch path.
- Cache signatures distinguish latest-only from archive-inclusive searches.
  Asking-price suggestions and verified SOLD / BUY rules are unchanged.

Source of the sort parameter: Tradera's own embedded search filter data in
tradera_sokning.html maps sortBy=AddedOn to Senast inlagda.

Validation: all 1,469 tests passed; source compilation and diff checks passed.
Includes actual Streamlit startup/rendering, mocked-browser crawler
page limits and early stop, progressive saving, archive retention, checkpoint
isolation, scope selection and cache separation. Live Tradera timings and
Streamlit deployment must be reported separately from local checks.
