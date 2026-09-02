# DATA_RESEARCH v0.11.3 – Incremental Full Market Crawl

## Mål
Kunna läsa in hela den relevanta Tradera-marknaden utan att göra en enda lång och CPU-tung körning på Streamlit Cloud.

## Arkitektur
- Smart uppdatering finns kvar för de nyaste annonserna.
- Nytt läge `market_batch` läser högst 12 sidor per sport och körning.
- Fortsättningspunkten sparas per sport i `tradera_fetch_state.json`.
- Alla hämtade annonser behålls i `tradera_data.json`; äldre annonser raderas inte när en ny smart uppdatering görs.
- Interaktiv fyndanalys arbetar fortfarande med ett begränsat arbetsset på högst 1 500 nyare annonser per sport. Detta är ett CPU-skydd, inte en begränsning av marknadsarkivet.
- Djupare marknadsomgångar detaljberikar högst två prioriterade annonser per sport för att hålla belastningen nere.

## Säkerhet
Marknadsscannern markeras som komplett först när Tradera returnerar en tom sida eller en upprepad resultatsida. Ett navigationsfel får inte felaktigt markera marknaden som färdigläst.
