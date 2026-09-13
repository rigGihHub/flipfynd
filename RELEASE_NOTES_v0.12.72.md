# FlipFynd v0.12.72 – Research Query Ladder

## Fokus
Öka träffsäkerheten i comp-research när marknadsplatser använder olika namn för samma kort, utan att sänka evidenskraven.

## Nytt
- Ny `research_query_ladder` bygger flera kontrollerade sökfraser från samma strukturerade research-identitet.
- Börjar med strikt sökning och provar därefter alternativ säsongsnotation, utan setnamn, utan parallel och en minimal kandidatfråga.
- Spelare + kortnummer behålls på alla användbara rungor.
- eBay Sold- och Tradera-länkar visas per sökvariant direkt i den automatiska comp-jakten.
- Breda träffar är uttryckligen researchkandidater; de kan aldrig automatiskt bli exact SOLD, värdering, maxpris eller KÖP.

## Varför
Efter förbättringarna av spelare/set/kortnummer är nästa hinder att samma kort ofta benämns olika på Tradera, eBay och prisguider. En enda exakt sträng missar därför legitima jämförelseobjekt.
