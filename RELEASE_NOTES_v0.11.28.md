# FlipFynd v0.11.28 — Persistent Database Activation

## What changed
- Created and verified a real Neon PostgreSQL backend for FlipFynd.
- Added a true database health probe instead of treating a configured URL as proof that storage is working.
- Persistent-storage UI now shows one of three clear states:
  - no database configured,
  - configured and verified,
  - configured but unreachable (local fallback active).
- Added lightweight metadata checks for the Flip Journal and sold-comp namespaces.
- Database health checks are cached for 60 seconds to avoid an unnecessary connection on every Streamlit interaction.

## Safety
- No database credentials are committed to the repository.
- Existing local fallback remains intact.
- No scoring, valuation, ranking, or buy-decision logic changed.

## Deployment
Set `FLIPFYND_DATABASE_URL` in Streamlit Secrets. Do not put the connection string in GitHub.
