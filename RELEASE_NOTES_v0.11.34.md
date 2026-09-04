# FlipFynd v0.11.34 – Unsynced Data Guard

## Varför
När PostgreSQL/Neon är konfigurerat men tillfälligt otillgängligt har FlipFynd tidigare fallit tillbaka till lokala JSON-filer. Det hindrade appen från att krascha, men skapade en viktig risk: en lokal ändring kunde finnas utan att användaren tydligt såg att databasen låg efter.

## Nytt
- Explicit lokal pending-sync-kö för `flip_journal` och `sold_comps`.
- En misslyckad databaswrite markeras nu som **osynkroniserad**, inte som lyckad persistent lagring.
- Den senaste kompletta namespace-snapshoten sparas med tidsstämpel och fingerprint.
- Så länge pending data finns läser FlipFynd den väntande lokala versionen i stället för att tyst återgå till en äldre databasversion.
- Persistent-lagringspanelen visar vilka dataytor som väntar på synkning.
- Ny explicit knapp: **Försök synka väntande data**.
- Pending-posten rensas först efter en lyckad databaswrite.
- Ingen automatisk merge görs mellan lokal och persistent data. Detta undviker tysta konflikter.
- Gamla storage-error-flaggor rensas efter en senare lyckad operation.
- Journalens lagringsstatus använder nu faktisk DB-health + pending-status, inte bara att en DB-URL finns.

## Säkerhetsprincip
Pending-kön är fortfarande Streamlit-runtime-lokal och är därför inte en backup eller ersättning för PostgreSQL. Vid längre DB-avbrott bör journalen exporteras. Funktionen minskar risken för **tyst divergens**, men kan inte göra runtime-lagring permanent.

## Modellpåverkan
Ingen. Ranking, värdering, sold-comp-regler och rekommendationer ändras inte.
