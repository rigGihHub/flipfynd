# FlipFynd v0.12.69 – Three-Anchor Identity Bootstrap

## Fokus
Öka research-recall när Tradera-rubriker saknar exakt ett kärnfält, utan att sänka KÖP- eller SOLD-kraven.

## Nytt
- Nytt `BOOTSTRAP`-läge i Exact Identity Gate.
- Player + tre av fyra kärnankare (spelare, set/program, säsong/år, kortnummer) kan nu starta kandidat-research även om ett fält saknas.
- `player + season + card number` får nu söka även när setnamnet saknas.
- `player + set + season` utan kortnummer förblir låst om ingen extra variantdiskriminator finns.
- NARROW-tröskeln är lätt sänkt för research-only sökning.
- Värdering, exact SOLD, maxpris och KÖP är fortsatt låsta tills strikt identitet är verifierad.

## Säkerhetsprincip
BOOTSTRAP är endast ett sätt att hitta möjliga identiteter/comps. Ett träffresultat måste fortfarande verifieras mot exakt kort innan det får påverka värdering eller köpbeslut.
