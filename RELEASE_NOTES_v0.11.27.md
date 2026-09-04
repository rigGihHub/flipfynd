# FlipFynd v0.11.27 – Persistent Storage Foundation

## Varför
Flip Journal och verifierade sold comps får inte långsiktigt vara beroende av Streamlit Community Clouds lokala filsystem. Streamlit dokumenterar att lokal lagring på Community Cloud inte garanteras vara persistent.

## Ändrat
- Ny `src/persistent_store.py` med PostgreSQL-baserad namespace-lagring.
- Stöd för `FLIPFYND_DATABASE_URL`, `DATABASE_URL` eller `[database].url` i Streamlit secrets.
- Flip Journal använder PostgreSQL när det är konfigurerat.
- Sold-comp-biblioteket använder PostgreSQL när det är konfigurerat.
- Första anslutningen kan migrera lokal data endast om den persistenta namespace-posten är tom.
- Databasfel stoppar inte hela appen: tydlig lokal fallback används och visas i UI.
- Ny statuspanel `💾 Persistent lagring`.
- Ingen hemlig databasadress läggs i repo eller ZIP.

## Säkerhetsprincip
Persistent historik används fortfarande inte automatiskt för att ändra modellvikter. Journalutfall och sold comps förblir separata datadomäner.

## Aktivering
Efter deploy kan en PostgreSQL/Neon-URL läggas in som Streamlit secret `FLIPFYND_DATABASE_URL`. Utan secret fungerar appen som tidigare med lokal JSON-fallback.
