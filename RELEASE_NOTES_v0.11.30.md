# FlipFynd v0.11.30 – Calibration Miss Analysis

## Varför
Outcome Calibration visar vilka signaler som fungerat. Den här releasen kompletterar det med den omvända frågan: **varför blev vissa verkliga affärer sämre än FlipFynd väntade sig?**

## Nytt
- Ny modul `src/calibration_miss_analysis.py`.
- Klassificerar endast avvikelser som stöds av sparade journalfält:
  - köp över rekommenderat maxpris,
  - försäljningsvärde tydligt lägre än prognos,
  - nettovinst tydligt lägre än prognos,
  - längre säljtid än prognos,
  - faktisk affär utan positiv nettovinst.
- Små normala avvikelser ignoreras för att minska brus.
- En misskategori måste ha minst 5 verkliga avslut innan den får lyftas som återkommande mönster.
- Felidentifierad variant/kortidentitet klassificeras **inte**, eftersom journalen ännu saknar en uttrycklig korrigeringslogg för det.
- Inga modellvikter ändras automatiskt.

## UX
Ny hopfällbar sektion i Flip Journal:
`🧭 Miss Analysis – varför blev utfallet sämre?`

Visar antal avslut, antal med tydlig avvikelse, avvikelseandel och vanligaste observerade orsaker.
