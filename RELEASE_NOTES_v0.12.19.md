# FlipFynd v0.12.19 – Pressure Research Drilldown

- Ny `src/pressure_research_drilldown.py`.
- Varje kort i Pressure Research Queue kan nu öppnas i ett eget drilldown.
- Drilldown visar exakt varför kortet lyfts: minskat observerat exact-supply, verifierade exakta SOLD och/eller högre observerad SOLD-median.
- Sparad exact-supply-historik visas med tidsstämplar och antal bekräftade/möjliga träffar.
- Verifierade exakta SOLD inom supply-perioden visas med datum och realiserat SEK-pris.
- Ny sektion: **Vad saknas innan KÖP ens kan övervägas?**
- Blockerare återanvänder befintligt underlag: exact identity, verifierade SOLD-comps, valuation display safety, valuation confidence, befintligt beslut och maxpris.
- Drilldown skapar ingen ny score, demand-signal, scarcity-score, värdering, maxpris eller KÖP.
- Frånvaro av blockerare är uttryckligen inte samma sak som KÖP.
