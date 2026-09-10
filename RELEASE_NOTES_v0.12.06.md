# FlipFynd v0.12.06 – Lot Treasure Hunter

- Ny `lot_treasure_hunter.py` prioriterar lotter/paket som förtjänar manuell kort-för-kort-granskning.
- En vanlig lot blir **inte** automatiskt en Treasure-kandidat. Det krävs minst en oberoende befintlig signal, exempelvis Information Edge, Hidden Find, visuell granskningssignal, dokumenterad samlarstruktur, missklassificering eller rookie-review.
- Hunter antar aldrig vilka kort som ingår i lotten, fördelar aldrig lotpriset till påhittade styckvärden och skapar aldrig KÖP eller marknadsvärde.
- Discovery Engine 2.0 får ett nytt `lot-treasure`-spår för lotter med extra evidens.
- Research-vyn känner nu igen lot/paket som ett separat granskningsbehov.
- Ny novice-expander **Lot Treasure – paket värda kort-för-kort-kontroll** visar upp till fem research-kandidater, varför de är intressanta och vad som måste verifieras först.
- v0.12.06 innehåller också en viktig import-hotfix: v0.12.05 anropade `build_bad_listing_queue` i UI utan motsvarande import i `app.py`. Detta hade kunnat ge `NameError` när den kodvägen kördes. Importen är nu tillagd och regressionstest finns.
- Ingen KÖP-, värderings-, maxpris-, sold-, risk- eller slutlig rankinglogik ändras.
