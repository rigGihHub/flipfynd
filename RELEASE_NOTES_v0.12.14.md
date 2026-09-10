# FlipFynd v0.12.14 – Exact Supply Confirmation

- Ny `src/exact_supply_confirmation.py`.
- Tradera-träffar från Exact Card Supply klassas först efter ordinarie FlipFynd-identitetsanalys.
- Tre utfall:
  - `CONFIRMED_EXACT` – kandidaten passerar Exact Identity Gate och matchar alla relevanta strukturerade identitetsfält.
  - `POSSIBLE_MATCH` – inga explicita konflikter, men identiteten är ofullständig eller för svag.
  - `WRONG_CARD` – minst ett strukturerat identitetsfält motsäger målkortet.
- Kritiska fält: spelare, set/program, säsong/år, kortnummer.
- Om målkortet har strukturerad parallel, grading company, grade eller serial denominator måste även dessa matcha.
- Ingen titelgissning används för att bekräfta exakt match.
- UI visar nu antal bekräftade exakta, möjliga och fel kort/konflikter för tidigare analyserade Exact Card Supply-träffar.
- Exact Supply Confirmation skapar aldrig KÖP, marknadsvärde eller maxpris.
