# Data research v0.11.27 – Persistent storage

Streamlit Community Cloud dokumenterar att lokal fillagring inte garanteras vara persistent och att runtime-genererade filer kan försvinna. Därför ska affärshistorik som Flip Journal och verifierade sold comps inte behandlas som hållbart sparade när de enbart ligger i appens lokala filsystem.

Release v0.11.27 inför därför ett valfritt PostgreSQL-lager med lokal fallback. Databasen lagrar separata JSON-namespaces för `flip_journal` och `sold_comps`. Befintlig lokal data får endast seedas när motsvarande persistent namespace ännu saknas, så att äldre runtime-data aldrig skriver över en redan etablerad databas.

Ingen extern databas är automatiskt skapad eller ansluten i denna release. Det kräver en separat databas-URL i Streamlit secrets.
