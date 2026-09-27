# FlipFynd v0.14.65

## Seller Quality Benchmark

- Lägger till ett versionsstyrt kvalitetsfacit för Seller Top 5.
- Håller observerade UI-regressioner, syntetiska säkerhetsfall och verkligt avslutade affärer i separata kohorter.
- Redovisar aldrig syntetisk kontraktstäckning som verklig precision eller recall.
- Stoppar releasekontraktet vid falskt KÖP, missad positiv kontroll, presentationsfel eller ogiltigt facitschema.
- Kräver explicit verifierat utfall innan en post får räknas som en verklig avslutad affär.

## Kapitalriskfixar

- Ett saknat eller explicit nollställt inköpspris kan inte längre få intern nivån `FIND`.
- Lotter och multipack är inte längre köpklara som singelkort, även om importerade comp- och vinstfält ser starka ut.
- Lotter kan fortfarande prioriteras i sitt separata manuella researchflöde.

## Verifiering

- 11 benchmarkfall: 100 % kontraktsprecision, kontraktsrecall och säkerhetsspecificitet.
- Dessa siffror är regressionsmått, inte uppmätt marknadsträffsäkerhet.
- Verklig precision/recall är fortsatt omätt tills verifierade avslut har samlats.
