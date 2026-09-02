# FlipFynd v0.5.5 – Kortnummer & checklistmatchning

- Identifierar konservativt kort-/checklistnummer som `#451`, `Card #451`, `No. 451` och alfanumeriska nummer som `#YG-23`.
- Håller isär checklistnummer från serialisering som `12/99` och `1/1`.
- Tar med kortnumret i den normaliserade kortidentiteten.
- Exakt checklistnummer får tydligt högre comp-likhet; olika checklistnummer straffas.
- Fem nya regressionsfall för kortnummer/checklistmatchning.
