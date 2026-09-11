# FlipFynd v0.12.25 – Coverage Gap Planner

- Market Coverage Autopilot bygger inte längre alltid hockey och fotboll samtidigt när båda är ofullständiga.
- Den använder senaste analyserade resultat som ett observationslager för att hitta vilken sport som har svagast fyndunderlag.
- Prioriteringssignaler: inga verifierade fynd, inga lovande kandidater, få analyserade kandidater, inga säkert visningsbara marknadsvärden, ofullständig täckning och sidluckor.
- Om senaste analys saknas används marknadstäckning som fallback; sporten med färre inlästa sidor prioriteras.
- Färskhet har fortfarande högsta prioritet. Om någon marknad är stale/due körs gemensam incremental refresh först.
- När marknaden byggs vidare hämtas nästa sidblock bara för den prioriterade sporten. Detta minskar onödig hämtning och lägger datakapacitet där fyndunderlaget faktiskt är svagast.
- UI visar varför en viss marknad prioriteras men lägger inte till fler huvudknappar.
- Ingen ny fyndscore skapas och ingen ranking-, värderings-, KÖP-, maxpris- eller risklogik ändras.
