# FlipFynd v0.12.68 – Research Identity Recovery Pass

## Fokus
Öka andelen annonser som kan få smal comp-research utan att sänka kraven för exact SOLD, värdering eller KÖP.

## Nytt
- Ny research-only titelåtervinning för marketplace-rubriker där säljaren utelämnar `#` framför kortnumret, t.ex. `1995-96 Pinnacle 101 Wayne Gretzky`.
- Bare checklist-nummer accepteras bara när titel redan innehåller spelare + set + säsong och exakt en rimlig sifferkandidat återstår.
- År, säsonger, serial fractions, tider och prisfragment filtreras bort innan recovery görs.
- Exact Identity Gate får nytt `TITLE_RECOVERED` researchläge.
- Researchåtervunna fält exponeras separat från beslutsstarka identity fields.
- Auto Comp Research använder research-identiteten för söklänkar, men strict identity för exact SOLD-matchning.
- Ingen title recovery kan ensam låsa upp marknadsvärde, maxpris eller KÖP.

## Princip
Mer recall där det är säkert att söka; samma precision där pengar och köpbeslut börjar påverkas.
