# FlipFynd v0.11.24 — Decision-First UX + Deployment Guard

## Fixat kritiskt deployfel
- `app.py` kraschar inte längre vid import om en äldre/stale `src/sold_comp_collector.py` saknar `smart_collect_local_sold_comps`.
- Hela FlipFynd startar då ändå; endast den valfria Smart Sold Comp Acquisition-funktionen stängs av med ett tydligt felmeddelande.
- Den kompletta releasen innehåller den korrekta moderna collector-filen, så skyddet är främst mot partiella eller osynkade deployer.

## Decision-First UX
- Resultatkortets förstavy fokuserar tydligare på beslut, total kostnad, realistiskt säljpris, nettovinst och säljbarhet.
- Exakt säljchansprocent tas bort från den mest framträdande snabbvyn och ersätts med kvalitativ säljbarhet.
- Fyndsäkerhet visas kvalitativt i förstavy i stället för att överbetona heuristiska exakta poäng.
- Information Edge, Market Edge, Hidden Find, Misclassified och Rookie-signaler sammanfattas på resultatkortet under ett gemensamt begrepp: **Informationsövertag**.
- En kort `Varför?`-rad lyfter de viktigaste beslutsunderlagen utan att ta bort full analys.

## Säkerhet
- Inga Hunter/Edge-signaler skapar värde eller KÖP-beslut.
- Existerande full analys och säkerhetsgrindar finns kvar bakom fördjupning.
