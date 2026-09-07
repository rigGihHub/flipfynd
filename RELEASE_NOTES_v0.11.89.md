# FlipFynd v0.11.89 – Best Available + Clear Market Fetch

## Resultat även när inget är KÖP
- Ny vy **Bästa tillgängliga just nu** visar upp till tre av de högst rankade redan analyserade alternativen när inget når KÖP.
- Vyn använder befintlig `opportunity_priority_score`, `deal_score` och confidence endast för ordning; den skapar inga nya scores.
- Befintligt KÖP/BEVAKA/SKIP-beslut bevaras ordagrant och ett svagt kort uppgraderas aldrig till KÖP.
- Fallbacken använder analyserade resultat inom den aktuella sökningen även om normala visningsfilter gömmer SKIP eller låg confidence.
- Om analysmotorn inte har några analyserade kandidater alls visas ingen påhittad Top 3.

## Tydligare avancerad marknadshämtning
- Fixar textfelet `hockeyHockey`.
- `Marknadstäckning` förklaras som **Läs in mer av marknaden**.
- `Smart Refresh` förklaras som **Fräscha upp äldre sidor**.
- Knappar och hjälptexter beskriver nu exakt om de läser nästa Tradera-sidblock eller återbesöker gamla sidor.

## Säkerhet
- Ingen köp-, ranking-, värderings- eller maxprislogik har ändrats.
