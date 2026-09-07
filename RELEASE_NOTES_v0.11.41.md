# FlipFynd v0.11.41 – Sold Data Acquisition Pipeline

- Ny källoberoende acquisition pipeline för CSV/JSON, framtida API:er och tillåtna feeds.
- Fail-closed: explicit realiserat pris krävs; valutakurser gissas aldrig.
- Felaktiga rader hamnar i synlig karantän i stället för att försvinna tyst.
- Dubbletter stoppas före lagring.
- Varje accepterad rad får batch/provenance-spårning.
- Varje verifierad försäljning routas direkt genom v0.11.40: EXACT_READY, IDENTITY_REVIEW, SALE_ONLY eller REJECTED.
- En riktig försäljning med osäker kortidentitet får fortfarande inte bli exact comp.
- Ingen scraper eller extern sold-integration påstås finnas.
