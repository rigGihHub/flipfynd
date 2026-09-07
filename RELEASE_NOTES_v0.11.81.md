# FlipFynd v0.11.81 – Momentum Source Intake

- Strikt source-intake för strukturerade Player Momentum-observationer.
- Källtyper: officiell liga, officiellt lag, officiell tillverkare, prospect-ranking, checklist-publisher och manuell research.
- Felaktig/otillräckligt attribuerad data avvisas.
- Källregister skiljer uttryckligen mellan tillåten källa och faktisk automatiserad integration.
- Registry innehåller NHL.com Prospects och Upper Deck Checklists som relevanta källroller men automated_ingestion=False.
- Ny bridge kopplar dokumenterade momentumspelare till redan skannade kort via strukturerat player_name.
- Titlar används inte för att gissa spelaridentitet i bryggan.
- Momentum ändrar aldrig befintligt KÖP/BEVAKA, värdering eller maxbud.
