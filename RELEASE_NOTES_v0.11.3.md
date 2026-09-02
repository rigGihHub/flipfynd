# FlipFynd v0.11.3 – Incremental Full Market Crawl

- Ny `MARKNADSSCANNER` i huvudvyn.
- `Läs nästa omgång` fortsätter där föregående omgång slutade.
- Varje omgång läser högst 12 sidor per sport.
- Hela annonsarkivet sparas; smarta uppdateringar raderar inte längre äldre marknadssidor.
- Fyndanalysen är fortsatt begränsad till ett snabbt arbetsset på 1 500 nyare annonser per sport.
- Marknadsstatus sparas separat för hockey och fotboll.
- Komplett-status kräver verkligt slut på resultat, inte ett tillfälligt hämtningsfel.
- Administratören kan starta om marknadsscanningen från sida 1 utan att radera sparade annonser.
- Detaljberikning i djupa marknadsomgångar begränsas till två annonser per sport för lägre CPU-belastning.
