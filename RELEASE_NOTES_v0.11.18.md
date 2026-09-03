# FlipFynd v0.11.18 — External Sold Source Adapter

## Varför
Den största flaskhalsen är fortfarande verkliga sold comps. v0.11.18 separerar därför **hämtning/källformat** från FlipFynds befintliga strikta validering.

## Nytt
- Ny adapterarkitektur i `src/external_sold_sources.py`.
- Förberedda format för generisk verifierad export, eBay och Tradera.
- En extern rad måste ha explicit såld-status eller explicit sold-flagga innan den ens når sold-comp-importen.
- `ended`/`closed` räcker inte.
- Befintlig valutagrind gäller fortfarande: utländsk valuta kräver explicit SEK-pris eller explicit FX-kurs.
- Ny UI-panel **External Sold Source Adapter** med CSV/JSON-import och avvisningsdiagnostik.
- Provenance sparas som `external_adapter:<källa>`.

## Viktig avgränsning
Denna release kopplar **inte** upp sig mot eBay eller Tradera och påstår inte att någon extern API-källa är verifierad. Den skapar det säkra gränssnitt som en sådan källa senare kan kopplas till.
