# Data research v0.11.17 — Smart Sold Comp Acquisition

Den här releasen lägger inte till nya externa prisantaganden och gissar inga försäljningar.

Accepterad såld-evidens:
- positivt explicit `sold_price`, eller
- explicit såld-status tillsammans med positivt pris.

Avvisas som sold comp:
- `ended`/`closed` utan direkt såld-evidens,
- aktivt/begärt pris utan såld-evidens,
- såld-status utan positivt pris,
- främmande valuta utan explicit SEK-pris eller explicit FX-kurs.

Smart acquisition söker bara i en begränsad allow-list av lokala FlipFynd-källor samt `data/sold_imports/*.json`. Den crawlar inte webben i denna release. Syftet är att öka automationen utan att sänka beviskraven.
