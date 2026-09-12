# FlipFynd v0.12.57 – Live Same-Seller Inventory Search

## Fokus
Samfraktsjakten kan nu hämta säljarens hela aktiva Tradera-lager via REST v4 i stället för att bara söka bland annonser som redan råkar finnas i FlipFynds lokala dataset.

## Nytt
- Ny read-only integration `src/tradera_seller_inventory.py`.
- Säljaralias löses till Tradera user id via `/v4/users/by-alias/{alias}`.
- Aktiva annonser hämtas via `/v4/items/seller/{userId}` med `filterActive=1`.
- Pris, frakt, annonslänk, sluttid och säljare normaliseras till FlipFynd-format.
- Samfraktsvyn kan slå ihop live-API-resultat med redan inlästa annonser och analyser.
- Upp till 30 säljarannonser visas i samfraktsjakten.
- API-fynd är discovery-data och blir aldrig automatiskt KÖP/add-on utan ordinarie analys och evidens.

## Säkerhetsprincip
Integrationen är strikt läsande. Den kan inte bjuda, köpa eller ändra annonser. Aktiv annons är inte SOLD-evidens.
