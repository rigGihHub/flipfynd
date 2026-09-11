# FlipFynd v0.12.34 – Rookie Window & Player Archetype

- Ny `rookie_window_context.py`.
- FlipFynd använder verifierat födelsedatum + observerat kortår/säsong för att beskriva ett karriärfönster.
- Karriärfönster: ungt, prime-age, etablerat, sent/historiskt eller okänt.
- Ett RC/rookie-anspråk kan markeras som kronologiskt rimligt eller kronologiskt tveksamt.
- Ett tidigt kort utan RC-anspråk blir inte automatiskt ett rookie-kort.
- Officiellt rookieår lämnas okänt tills det verifierats via checklist-/programdata.
- Ny Player Archetype kombinerar verifierad aktivitet/livscykel med befintlig player-market-tier utan att hitta på legend-/prospect-status.
- UI visar spelararketyp + karriärfönster och varnar för kronologiskt tveksamma rookie-anspråk.
- Modulen skapar aldrig marknadsvärde, ROI, maxpris eller KÖP.
