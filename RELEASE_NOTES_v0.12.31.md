# FlipFynd v0.12.31 – Player × Card Hierarchy

- Ny `src/player_card_hierarchy.py`.
- FlipFynd kombinerar nu spelarens befintliga market score/tier med den dokumenterade Card Hierarchy Engine.
- Samma kortprogram behandlas därför olika beroende på spelarefterfrågan:
  - elitspelare + central/premium korthierarki,
  - stark spelare + relevant samlarprogram,
  - stjärnspelare + standardkort,
  - premiumstruktur + svag/okänd spelare,
  - selektiv/svag kombinerad profil.
- Rookie-status får extra tyngd endast när både programmet och spelarefterfrågan stödjer det.
- Ny hobbyfälla: prestigefyllt set/program gör inte automatiskt en svag spelare värdefull.
- Ny hobbyfälla: elitspelare gör inte varje bas/standardkort premium.
- Marknadsevidens och identitet används för att ange evidenssäkerhet, inte för att hitta på pris.
- Karriärstatus (prospect/veteran/legend) **gissas inte** eftersom nuvarande player-market-data saknar verifierad career-status metadata.
- Huvudkort visar nu **Spelare × kort** med kombinerad samlarprofil och evidenssäkerhet.
- Modulen skapar aldrig marknadsvärde, maxpris eller KÖP.
