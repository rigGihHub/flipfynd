# FlipFynd v0.11.83 – Momentum Change Detector

- Ny `src/momentum_change_detector.py`.
- Jämför attribuerade, tidsstämplade snapshots för samma spelare och mätvärde.
- Stöder både numeriska förändringar (med faktisk delta) och kategoriska förändringar.
- Oförändrade observationer skapar ingen signal.
- Ofullständiga/otillskrivna snapshots avvisas.
- Ingen talangscore, sannolikhet, kausal tolkning, KÖP, värdering eller maxbud skapas.
- Förbereder nästa steg: persistent snapshot history + koppling till Stjärnskott Radar och verklig SOLD-marknadsreaktion.
