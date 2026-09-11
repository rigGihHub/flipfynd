# FlipFynd v0.12.28 – Segment Yield Learning

- Ny `src/segment_yield_learning.py`.
- FlipFynd mäter nu observerad analys-yield per marknadssegment: prisband + annonsform + single/lot.
- Yield mäts på befintliga utfall: verifierade fynd, lovande kandidater, säkert visningsbara värden och exact identity.
- Ett segment behöver minst 8 analyserade kandidater innan det får etiketten verifierad/lovande/låg observerad yield.
- Mindre stickprov markeras `OTILLRÄCKLIGT_UNDERLAG`.
- Verifierad yield använder samma evidenskrav som novice decision tiers: KÖP, >=60 säkerhet, >=2 verifierade SOLD, exact identity och säkert visningsbart marknadsvärde.
- Ny expander i huvudvyn: **Vilka delar av marknaden ger bäst fyndunderlag?**
- Systemet är observationsbaserat. Det ändrar inte automatiskt analysbudget, segmenturval, KÖP, värdering, maxpris eller riskregler.
