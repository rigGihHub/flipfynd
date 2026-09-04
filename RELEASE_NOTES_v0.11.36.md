# FlipFynd v0.11.36 – Decision Conflict Audit

## Syfte
Den här releasen gör slutbeslutet mer robust genom att fånga när olika delar av analysen säger emot varandra. Ett kort ska inte se ut som ett tydligt KÖP enbart för att fyndpoängen är hög om risk, säljbarhet, nedsida eller evidens samtidigt talar emot caset.

## Nytt
- Ny modul `src/decision_conflict_audit.py`.
- Audit av konflikter mellan:
  - hög fyndpoäng och hög risk,
  - hög fyndpoäng/vinst och låg säljbarhet,
  - positiv förväntad vinst och negativt golvscenario,
  - KÖP-signal och låg säljchans,
  - mycket hög fyndpoäng och tunn värderings-/identitetssäkerhet,
  - hög fyndpoäng utan verifierade sold comps,
  - extrem ROI och tunn värderingsevidens.
- Konflikter klassas som `moderate` eller `hard`.
- Ett KÖP kan endast sänkas till KANSKE vid minst en hård konflikt eller minst tre oberoende måttliga konflikter.
- Audit kan aldrig skapa eller uppgradera ett köpbeslut.
- Vid allvarlig konflikt blockeras dynamiskt maxköp/maxbud.
- Fyndpoängen räknas om efter eventuell nedgradering så att UI och beslut inte säger olika saker.
- Ny fullanalyssektion: `⚖️ Decision Conflict Audit`.
- Primärresultatet visar tydlig varning om KÖP stoppats av motstridiga signaler.

## Produktprincip
En stark fyndsignal är inte samma sak som ett starkt köpbeslut. FlipFynd ska hellre säga “ser billigt ut, men underlaget/riskbilden håller inte ihop” än ge ett självsäkert KÖP på motsägelsefull data.

## Säkerhet
- Ingen ny värderingsmodell.
- Ingen automatisk modellkalibrering.
- Ingen uppgradering till KÖP.
- Inga nya externa datakällor.

## QA
- `python -m pytest -q`: 410 tester passerade.
- `python -m compileall -q app.py src tests`: passerade.
- ZIP-integritet: verifierad.
- Live Streamlit: inte deployad eller live-verifierad i denna release.
