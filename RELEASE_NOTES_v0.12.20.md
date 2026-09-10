# FlipFynd v0.12.20 – Research Action Center

- Ny `src/research_action_center.py`.
- Pressure Research Drilldown visar nu **Nästa bästa researchsteg**.
- Åtgärder skapas endast från redan observerade luckor i underlaget.
- Exempel: verifiera kortnummer, verifiera spelare/set/säsong, verifiera parallel/numrering, hitta saknade verifierade SOLD, kontrollera exact supply, ta ny supply-snapshot eller granska värderingsunderlaget.
- Om exakt en SOLD saknas står det tydligt **Hitta 1 verifierad SOLD till**.
- Åtgärder prioriteras deterministiskt; ingen ny opportunity-score skapas.
- Att visa en åtgärd skapar inte identitetsfakta, SOLD-evidens, värdering, maxpris eller KÖP.
- Utförd research måste fortfarande passera respektive befintlig verifieringsgrind innan analysen får ändras.
