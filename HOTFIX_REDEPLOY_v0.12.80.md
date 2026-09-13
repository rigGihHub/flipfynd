# FlipFynd v0.12.80 hotfix redeploy

Forces a clean Streamlit Cloud redeploy after an import error where `app.py` imported `research_identity_failure_diagnostics` from `src.research_shortlist`, even though the function is present in `main`.

No decision logic changed.
