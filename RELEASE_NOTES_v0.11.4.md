# FlipFynd v0.11.4 – Market Coverage & Freshness

## Nytt
- Marknadsscannern visar nu separat täckning för hockey och fotboll.
- FlipFynd visar hur långt den sammanhängande fullmarknadsläsningen har kommit utan att hitta på en procentsats innan marknadsslutet är känt.
- När slutet faktiskt har nåtts visas 100 % / hela marknaden inläst.
- Färskhet visas per sport: Färsk, Behöver snart uppdateras eller Gammal – uppdatera.
- Varje inläst sida får en tidsstämpel för framtida färskhetskontroller.
- Luckor i sidtäckningen visas om sådana finns.

## Tydligare knappar
- `Uppdatera annonser`: snabb daglig kontroll från sida 1 efter nya/förändrade annonser.
- `Läs nästa omgång`: fortsätter den stegvisa fullmarknadsläsningen där den slutade.
- Admin-knapparna har nu korta förklaringar direkt i gränssnittet.
- `Börja om full marknadsläsning` förklarar tydligt att sparade annonser inte raderas.

## Säkerhet/prestanda
- Fyndanalysen fortsätter använda ett begränsat aktivt arbetsset per sport.
- Hela insamlade marknaden kan ändå ligga kvar sparad.
