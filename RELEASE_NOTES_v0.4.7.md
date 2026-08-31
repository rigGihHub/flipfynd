# FlipFynd v0.4.7 – Rookie program hierarchy

## Förbättringar
- Rookieprogram identifieras nu separat från en generisk `Rookie/RC`-etikett.
- Hockey: Young Guns, Young Guns Canvas, Future Watch, Future Watch Auto och Marquee Rookie får egna signaler.
- Fotboll: Rated Rookie, Prizm Rookie, Topps Chrome Rookie, Merlin Rookie och Select Rookie identifieras.
- Young Guns och Future Watch kan identifieras som rookiekort även när annonsrubriken saknar ordet `rookie` eller `RC`.
- Rookiepremien graderas efter både rookieprogram och faktisk spelarefterfrågan.
- Ett känt rookieprogram kan inte ensamt göra en svag spelarmarknad till ett fynd.
- Generiska rookieetiketter utan identifierat set/program får en tydlig osäkerhetsflagga.

## QA
- 34/34 unittest-tester godkända.
- Projektet kontrollerat med `python -m compileall` utan syntaxfel.
