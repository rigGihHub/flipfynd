# DATA RESEARCH – v0.10.2

## Player × Card Demand Engine

Den här releasen bygger vidare på FlipFynds kunskapsbank genom att separera tre frågor som tidigare låg närmare varandra:

1. **Hur efterfrågad är spelaren?**
2. **Hur samlarrelevant är kortstrukturen?**
3. **Finns observerad omsättning som stödjer efterfrågan?**

Modellen är uttryckligen **inte en prisguide**. Den använder inga multiplikatorer för marknadsvärde och får inte höja värde, vinst, ROI eller maxbud.

### Tre komponenter

- **Spelarefterfrågan 0–100**: befintlig konservativ spelarprofil i `data/player_market.json`.
- **Kortstruktur 0–100**: bygger på Variant Ladder, Rookie Hierarchy och Grail/Chase-kunskap.
- **Marknadsevidens 0–100**: verifierade sold comps och observerad omsättning väger tyngst. Aktiva annonser är endast svagt stöd.

### Viktig tolkningsregel

Avsaknad av sold comps betyder **otillräckligt underlag**, inte automatiskt låg efterfrågan. Därför får marknadskomponenten ett neutralt, försiktigt grundvärde när försäljningshistorik saknas.

### Guardrails

- Okänd spelare kan inte få elitklassning bara tack vare ett sällsynt kort.
- Sällsynt kortstruktur + svag spelarefterfrågan får en tydlig cap.
- Låg kortidentitet sänker efterfrågeklassningen.
- Aktiva annonser får aldrig likställas med faktisk omsättning.
- Motorn får användas för **vilka annonser som ska fullanalyseras först**, men inte för slutlig prisvärdering eller ranking av ekonomiskt utfall.

### Ny analysprioritering

Player × Card Demand Engine producerar en separat **analysprioritet 0–100**. Den kan ge högst 12 poäng extra i urvalet till full analys. Det innebär att en känd premiumkorttyp på en starkt efterfrågad spelare inte lika lätt missas av den billiga första analysen, samtidigt som den slutliga rankingen fortfarande styrs av faktisk ekonomi, risk och comps.
