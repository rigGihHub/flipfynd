# FlipFynd v0.12.18 – Pressure Research Queue

- Ny `src/pressure_research_queue.py`.
- Market Pressure används nu för att skapa en **manuell researchkö**, aldrig en KÖP-lista.
- En exakt kortidentitet kan prioriteras när tre redan observerade fakta sammanfaller:
  1. observerat exact-supply har minskat,
  2. minst en verifierad exakt SOLD med pris finns i supply-perioden,
  3. observerad verifierad SOLD-prismedian är högre i senare delen av perioden.
- Två av tre fakta ger `RESEARCH`; alla tre ger `PRIORITERA_RESEARCH`.
- Detta är deterministisk evidenssortering, inte en ny opportunity score.
- Kön deduplicerar per exakt identitetsnyckel.
- Inga aktiva annonser räknas som SOLD.
- Ingen demand-signal, scarcity-score, marknadstrend, värdering, maxpris eller KÖP skapas.
- Ny novice-expander: **Pressure Research – kort värda extra kontroll**.
