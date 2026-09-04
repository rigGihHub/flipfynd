# Data Research v0.11.34 – Persistence Failure Semantics

FlipFynds historiska data blir allt viktigare för Outcome Calibration och sold-comp-värdering. Därför är det inte acceptabelt att en PostgreSQL-write misslyckas och att appen sedan presenterar lagringsläget som om allt vore synkat.

v0.11.34 inför en enkel fail-safe semantik:

1. Databaswrite lyckas → persistent data är auktoritativ och eventuell pending snapshot rensas.
2. Databaswrite misslyckas → senaste kompletta snapshot sparas lokalt som explicit pending data.
3. Pending data finns → FlipFynd visar pending-versionen och markerar den som osynkroniserad.
4. Retry lyckas → hela snapshoten skrivs till dess namespace och pending-markeringen rensas.
5. Ingen automatisk rad-för-rad-merge görs, eftersom appen saknar konfliktmetadata som säkert kan avgöra vilken version som är rätt.

Detta är avsiktligt konservativt. En tydlig osynkroniserad status är bättre än en osäker automatisk merge.
