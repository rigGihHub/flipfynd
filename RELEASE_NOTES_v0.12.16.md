# FlipFynd v0.12.16 – Supply vs Sales Monitor

- Ny `src/supply_vs_sales_monitor.py`.
- Exact Supply History jämförs nu med verifierade exakta SOLD-poster för samma strukturerade kortidentitet.
- SOLD räknas bara om posten passerar både verifierad försäljning och exact-identity-intake.
- Vanliga aktiva annonser räknas aldrig som SOLD.
- När minst två supply-snapshots finns räknas verifierade exakta SOLD inom perioden mellan första och senaste snapshot.
- Resultatet är strikt deskriptivt. Exempel: *observerat exact-supply minskade samtidigt som verifierade exakta försäljningar registrerades*.
- Detta är inte bevis för efterfrågan, knapphet eller undervärdering.
- Ingen demand-signal, scarcity-score, värdering, maxpris eller KÖP skapas.
- Exact Card Supply-vyn visar nu Supply vs SOLD när tidsunderlaget räcker.
