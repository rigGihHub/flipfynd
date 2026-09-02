# FlipFynd v0.6.7 – Comp Match Guardrails

## Varför denna release
v0.6.6 kunde samla verifierade avslut, men marknadsanalysen kunde fortfarande låta en tydligt annan kortvariant vara kvar som comparable om den totala likhetspoängen ändå blev hög nog. Det kan ge kraftigt fel marknadsvärde, särskilt för grade, serial numbering, named parallels, checklistnummer och säsong.

## Ändrat
- Ny `assess_comp_compatibility()` körs före den vanliga likhetspoängen.
- En comp diskvalificeras när båda objekten explicit identifierar men motsäger varandra på:
  - kortnummer/checklistnummer
  - säsong
  - serial numbering, t.ex. /25 kontra /99
  - grade, t.ex. PSA 10 kontra PSA 9
  - named parallel, t.ex. Silver Outburst kontra Gold Outburst
- Saknad information räknas inte som motsägelse. FlipFynd gissar alltså inte att ett kort är base/ungraded bara för att rubriken saknar detaljen.
- Diskvalificerade comps kan inte påverka market benchmark, Low/Base/High eller sold-comp confidence.
- Full analys visar hur många comps som uteslutits och varför.
- Analyscachemodell höjd så äldre comp-resultat inte återanvänds.
- Synligt versionsnummer: v0.6.7.

## QA
- `python -m compileall -q .` godkänd.
- `python -m unittest discover -s tests -v`: 122/122 tester passerar.
- Nya tester verifierar hård diskvalificering för kortnummer, säsong, named parallel, serial denominator och grade, samt att saknad variantinformation inte feltolkas som konflikt.
- Separat test verifierar att tre verifierade sålda comps med fel parallel inte kan skapa marknadsvärde för målobjektet.

## Inte verifierat
- Ingen live-verifiering på Streamlit.
- Ingen extern live-hämtning av sold comps från Tradera/eBay/Cardmarket verifierad i denna release.
