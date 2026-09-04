# DATA RESEARCH v0.11.28 — Persistent Database Activation

## Goal
Activate a real persistent PostgreSQL backend for FlipFynd and make storage health visible without exposing credentials.

## Implemented
- A dedicated Neon PostgreSQL project named `FlipFynd` was created in EU Central.
- The `flipfynd_state` table was created.
- Namespaces for `flip_journal` and `sold_comps` were initialized.
- The database was queried successfully after creation.
- FlipFynd now distinguishes between a configured database URL and a database that is actually reachable.
- The health check uses a lightweight read-only `SELECT 1` and is cached in Streamlit for 60 seconds.
- Namespace status exposes metadata only; payload contents and credentials are never shown.

## Security
- The database connection string is NOT stored in source code, ZIP files, release notes, or GitHub.
- Streamlit must receive it through `FLIPFYND_DATABASE_URL` in Secrets.
- Local JSON remains a fallback when PostgreSQL is not configured or cannot be reached.

## Deployment limitation
The release cannot modify Streamlit Community Cloud secrets automatically. A one-time secret entry is still required in Streamlit settings.
