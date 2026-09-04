# FlipFynd v0.11.25 – Market Command Center

## Mål
Förenkla den dagliga marknadshämtningen utan att ta bort avancerad kontroll.

## Ändrat
- Förstavyn visar nu en enkel marknadsstatus för hockey och fotboll.
- En huvudknapp, **Uppdatera marknaden**, uppdaterar normalt båda sporterna från de nyaste Tradera-sidorna.
- Fullmarknadsscanner, Smart Refresh, sidtäckning och sportstyrning ligger nu bakom **Avancerad marknadshämtning**.
- Ny ren statuslogik i `src/market_overview.py`; den påverkar inte ranking, värdering eller köpbeslut.
- APP_VERSION uppdaterad till v0.11.25.

## Säkerhetsprincip
Den förenklade statusen får inte låtsas att ofullständig täckning är fullständig. Den skiljer mellan färsk/redo, användbar men fortfarande under uppbyggnad, behöver uppdateras och okänd status.
