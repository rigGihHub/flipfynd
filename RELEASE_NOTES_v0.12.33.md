# FlipFynd v0.12.33 – Player Knowledge Base

- Ny separat `data/player_knowledge.json` för källstödd spelarkunskap.
- 15 första verifierade spelare över hockey och fotboll.
- Faktafält kan omfatta: aktiv/pensionerad, position, lag/klubb, födelsedatum, era, källa och verifieringsdatum.
- Player Knowledge hålls separat från player-market-score så att fakta och marknadspoäng inte blandas ihop.
- Ny livscykelkontext härleds endast från verifierad aktivitet + födelsedatum: ung aktiv, aktiv, sen aktiv fas eller pensionerad.
- Saknad kunskap lämnas okänd och gissas aldrig.
- Analyzer och huvudkort visar verifierad spelarkunskap där den finns.
- Ny diagnostik visar Player Knowledge-täckning per sport.
- Ingen spelarkunskap skapar ensam marknadsvärde, ROI, maxpris eller KÖP.
