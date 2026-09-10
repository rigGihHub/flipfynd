# FlipFynd v0.12.13 – Exact Card Supply Check

- Ny `src/exact_card_supply.py`.
- Exakt supply-sökning kräver att kortet redan passerar `Exact Identity Gate` för `supports_exact_comp_search`.
- Sökfrågan byggs endast av strukturerade fält: spelare + set/program + säsong/år + kortnummer. Parallel/gradering läggs bara till om de redan är explicit strukturerade.
- FlipFynd räknar exakta identitetsmatchningar i den redan analyserade aktiva kandidatpoolen med samma Exact Identity Gate.
- Tradera API kan kontrolleras på två söksidor med den exakta strukturerade sökfrågan.
- API-träffar kallas uttryckligen **kandidater**, inte bekräftade exakta exemplar. De läggs i kandidatunderlaget och måste därefter passera vanlig FlipFynd-identitetsanalys.
- Ingen titelgissning används för att bekräfta exakt kortidentitet.
- Exact Card Supply skapar aldrig KÖP, marknadsvärde eller maxpris.
- Ny novice-expander: **Exact Card Supply – kontrollera just det här kortet**.
