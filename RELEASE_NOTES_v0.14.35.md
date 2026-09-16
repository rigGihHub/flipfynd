# v0.14.35 — fix search submission after a running deployment

The v0.14.34 app passed include_older to build_search_run_signature. A running
Streamlit process retaining the earlier imported helper rejects that argument,
raising TypeError before analysis starts. Reproduced by pressing Hitta fynd in
Streamlit AppTest with the earlier helper signature.

- Encode latest/archive scope in the existing data_version argument. No module
  reload or new export is required; old and current helpers both work.
- Keep the scopes in distinct cache entries and preserve cache reuse for an
  unchanged search.
- Move cache setup inside the analysis error/status handler.
- Runtime tests submit the real search form, switch to older listings, submit
  again and check repeated-search cache reuse with both helper versions.

This fixes a regression from v0.14.34. Fetch limits, valuation and buy gates are
unchanged. Local runtime tests do not verify the live Streamlit deployment.

Validation: 1,471 tests passed. Source compilation and diff checks passed.
