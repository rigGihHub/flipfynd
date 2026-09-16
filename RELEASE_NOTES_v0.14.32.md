# v0.14.32 — fix seller badge import during app startup

The reported Streamlit screenshot shows ImportError at the seller_top5 import.
Fresh v0.14.31 starts successfully locally. Removing the newly added
seller_result_badge export from the loaded module reproduces an ImportError on
that same app.py line. This is consistent with an older loaded module during
deployment; the production traceback is redacted and its complete logs were
not available for verification.

Remove the new named import from app.py. Render the badge directly from the
final seller result tier already computed for the find/research heading. No
fallback grants BUY from decision text alone, and the risk gate is unchanged.

Add real Streamlit AppTest coverage for current and older loaded modules,
plus seller-result rendering with valid versus excessive risk. The missing
export test failed before this fix with the reported import location. All four
runtime tests pass after the fix; the full suite passes 1,421 tests.

The earlier syntax-only startup check could not detect this mixed-module
runtime failure. The new runtime tests run in the normal CI pytest suite.
Live deployment remains to be verified separately.
