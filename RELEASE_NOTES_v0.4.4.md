# FlipFynd v0.4.4 – Auction risk guard

## Fokus
Gör fyndmotorn mer realistisk för Tradera-auktioner jämfört med Köp nu-annonser.

## Ändringar
- Förbättrad identifiering av annonsform och stöd för strukturerat `sale_type` när det finns.
- Köp nu analyseras fortsatt på den faktiska visade inköpskostnaden.
- Auktioner får en konservativ säkerhetsmarginal i fyndkalkylen eftersom aktuellt/utropspris inte är ett garanterat slutpris.
- Säkerhetsmarginalen är 12 % av annonspriset, minst 15 kr och högst 75 kr.
- Det faktiska visade totalpriset behålls separat; den buffrade kostnaden används bara i risk-, ROI-, vinst- och köpbeslutslogiken.
- Auktioner märks med riskflaggan `auktionspris kan stiga före avslut` och får en förklarande analysorsak.
- Nya regressionstester för Köp nu, billiga auktioner, dyra auktioner och analysens kostnadsskillnad.

## Verifiering
- `python -m compileall -q .` – OK
- `python -m unittest tests.test_quality -v` – 19/19 tester OK

## Ej verifierat
- Ingen push/deploy eller liveverifiering i Streamlit har gjorts i denna release.
