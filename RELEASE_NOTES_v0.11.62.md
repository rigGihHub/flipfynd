# FlipFynd v0.11.62 – Comp Quality Guard

- Ny fail-closed kvalitetsgrind ovanpå redan verifierade Exact-comps.
- Återanvänder befintliga FlipFynd-säkerhetsregler: minst 3 Exact-comps, högst 45% relativ prisspridning och 180 dagar som färskhetsfönster.
- Statusar: READY, THIN, DISPERSED, STALE, MISSING_DATES, BLOCKED och NO_EXACT_COMPS.
- Saknade försäljningsdatum ger inte falsk färskhet; helt saknade datum blockerar beslutsstarkt stöd.
- Framtida datum blockeras som orimliga historiska bevis.
- Exact Identity och verifierad SOLD är fortfarande grundkrav. Near/Player-only blir aldrig värderingsgrund.
- Samma kvalitetsvy visas även för Exact premium-comps.
- Ingen ny prismodell, viktning eller automatisk förändring av KÖP-beslut.
