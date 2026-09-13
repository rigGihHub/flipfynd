# FlipFynd v0.12.67 – Identity Bottleneck Diagnostics & Narrow Research Lane

## Fokus
Attackera den verkliga läckan bakom 6/919 sökbara identiteter utan att sänka KÖP- eller värderingskraven.

## Nytt
- Ny diagnostik visar vilka identitetsankare som saknas: spelare, set/program, säsong/år, kortnummer samt konflikt/lot.
- Research identity får ett separat **NARROW**-läge när exakt ett kärnfält saknas men övriga identitetsankare plus kortnummer/variant gör sökningen tillräckligt smal.
- NARROW får bara bygga researchfrågor; den kan aldrig låsa upp exact SOLD, marknadsvärde, maxpris eller KÖP.
- Researchkön prioriterar nu `RESEARCH_READY_NO_SALES` före helt identitetslåsta kort.
- Parsern känner igen fler vanliga äldre set (Pinnacle, Score, Fleer, SkyBox, Pacific, Pro Set, Stadium Club, Bowman).
- Fallback-spelarparsern filtrerar fler produkt-/programord så att märkesnamn inte lika lätt misstolkas som spelare.

## Princip
Mer recall i researchledet, samma höga precision i beslutsgaten.
