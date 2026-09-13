# FlipFynd v0.12.71 – Research Set/Program Recovery

## Fokus
Öka andelen annonser som kan få en smal research-identitet när set/program saknas i den statiska setkatalogen.

## Nytt
- Ny research-only återvinning av set/program från vanliga marknadsplatsrubriker av typen `säsong + produkt + kortnummer + spelare`.
- Stöd för okända men tydligt märkta produkter som exempelvis `Panini Mosaic Premier League`, `Topps Match Attax UCL` och `Upper Deck Series 1` utan att varje produkt först måste hårdkodas i `SET_PATTERNS`.
- Återvinning kräver tillverkar-/kortvarumärkesankare och avvisar generiska segment som `Rare Hockey Card`.
- Kända set från den strikta parsern har fortsatt företräde.
- Återvunnet set/program är endast researchstöd och får inte ensamt låsa upp exact SOLD, värdering, maxpris eller KÖP.

## Säkerhetsprincip
Bredda sökbarheten utan att bredda beslutsbehörigheten.
