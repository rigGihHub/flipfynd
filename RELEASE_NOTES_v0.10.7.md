# FlipFynd v0.10.7 – Smart Listing Detail Enrichment

## Nytt

- Selektiv öppning av prioriterade Tradera-annonser på detaljsidan.
- Standardgräns: högst 12 detaljannonser per kategori och hämtning.
- Discovery-score 0–100 för vilka annonser som förtjänar djupare hämtning först.
- Försök att samla:
  - full annonsbeskrivning,
  - fler bildreferenser,
  - budantal,
  - sluttidstext,
  - säljartext,
  - detaljsidans titel/metadata.
- Full beskrivning används som kompletterande identitetsevidens; titelkonflikter skrivs inte över.
- Detaljbilder slås ihop med befintliga bilder för efterföljande visuell kontroll.
- Tidigare lyckad detaljberikning bevaras vid senare kategoriuppdateringar.
- Ny UI-expander: `🔍 Smart Listing Detail Enrichment`.
- Översikten visar hur många annonser som har detaljberikats.

## Robusthet

- Detaljberikning är fail-soft: problem på objektsidan stoppar inte hela kategori-crawlen.
- Nytt CLI-val `--detail-limit`; `0` stänger av detaljberikning.
- Rookie-programmatchning rättad så synonymregler kan vara `patterns_any` medan sammansatta krav använder `patterns_all`.

## Guardrails

Detaljberikningen skapar inte i sig marknadsvärde, vinst, ROI, maxbud eller köpbeslut.

## QA

- `python -m compileall -q .`: godkänd.
- `python -m pytest -q`: 252/252 tester passerar.
- Separat smoke test verifierade att full beskrivning kan komplettera identitetsanalysen och att bud/sluttid kan parsas från detaljtext.
- Ingen live-verifiering mot Tradera/Streamlit har gjorts i denna release.
