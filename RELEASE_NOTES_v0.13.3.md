# FlipFynd v0.13.3

- Återställer den senast inlästa aktiva marknaden från PostgreSQL efter en Streamlit-omstart eller deploy.
- Sparar varje uppdaterad marknadssnapshot persistent när databas är konfigurerad.
- Skickar den redan konfigurerade databasadressen säkert till den separata hämtprocessen; inga hemligheter sparas i koden.
- Fortsätter använda lokal JSON som säker fallback om databasen tillfälligt inte kan nås.
