# FlipFynd v0.12.45 – Collectible Hierarchy & Current Checklist Sweep

## Nytt
- Ny källstyrd samlarhierarki som skiljer mellan flagship rookie, key insert, numrerad parallel, källstyrd SSP/ultra-rare, published-odds chase, case-level hit, 1/1 och marknadsförings-chase utan kvantifierad knapphet.
- Hierarkin beskriver hobby-/checkliststruktur och får aldrig ensam skapa pris, ROI, maxbud eller KÖP-signal.
- `detect_market_knowledge_signals()` exponerar nu samlarhierarkin direkt för analys- och förklaringslagret.
- Raritetsförklaringen visar hierarkilabeln bredvid käll-/oddsstatusen.

## Knowledge sweep
- Lade till officiellt källstöd för 2025-26 Topps Chrome UEFA Club Competitions.
- Budapest at Night, Black Lazer Autographs, Metaverse och Bionic lagras konservativt som tillverkarens chase/exclusive-program när exakt odds/print run inte framgår av produktsidan.
- Ingen av dessa etiketter uppgraderas automatiskt till SSP eller case hit utan kvantifierat eller explicit källstöd.

## QA
- Nya regressionstester för hierarkiklassning, publicerade odds, numrerade parallels och marknadsförings-chase.
