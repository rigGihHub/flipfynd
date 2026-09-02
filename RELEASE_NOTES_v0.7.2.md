# FlipFynd v0.7.2 – Smart Riskmodell

## Vad som ändrats
- Ny separat riskmodell 0–100 med nivåerna Låg / Medel / Hög.
- Risk bedöms utifrån värderingssäkerhet, kortidentifiering, säljbarhet, annonskvalitet, verifierade avslut, diskvalificerade comps, prisvariation, spelar-ID, lot/paket, extrem prisavvikelse och auktion.
- Risk är separerad från Fyndsäkerhet och Fyndpoäng: hög risk betyder inte automatiskt dålig affär, men rekommendationen blir försiktigare.
- Hög risk kan demotera ett tydligt KÖP till BEVAKA/KANSKE och ett starkt fynd till vanligt KÖP.
- Fyndpoängen får nu ett explicit riskavdrag från riskmodellens score i stället för att enbart räkna antal varningsflaggor.
- Rekommenderat maxpris/maxbud riskjusteras. Låg risk använder 98 % av normal kalkyl, medelrisk 90 %, hög risk normalt 78 % och mycket hög risk kan sänka taket till 70 %.
- Resultatkortet visar Risk och hur mycket maxbudskalkylen riskjusterats.
- Full analys visar risknivå och en förklaring till vilka faktorer som driver risken.
- Analyscacheversion höjd till `flip_v11_smart_risk_model`.
- Synligt versionsnummer höjt till v0.7.2.

## Viktigt
Riskmodellen bygger endast på data som faktiskt finns i analysen. Den hittar inte på comps, prisvariation eller identifieringsfakta. Saknade verifierade avslut behandlas som osäkerhet.

## QA
- `python -m compileall -q .` godkänd.
- `python -m unittest discover -s tests -p 'test_*.py'`: 152/152 tester godkända.
- Nya tester täcker låg/hög risk, prisvariation, riskens påverkan på fyndpoäng och riskjusterat maxbud.
- Ingen live-verifiering mot Streamlit eller aktuella Traderaannonser är gjord i denna release.
