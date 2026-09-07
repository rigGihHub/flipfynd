# FlipFynd v0.11.86 – Four-Way Navigation

## Fokus
Gör huvudflödet begripligt för en oerfaren användare utan att förenkla beslutsmotorn.

## Nytt
- Ny huvudfråga: **Vad vill du göra?**
- Fyra primära vyer:
  - **Vad ska jag köpa?**
  - **Slutar snart**
  - **Bevaka**
  - **Research**
- Nybörjarvyerna visar bara handlingsrelevant information.
- Hela tidigare analysterminalen finns kvar bakom **Visa fördjupad analys**.
- `src/novice_navigation.py` organiserar befintliga analyser men skapar aldrig nya köpbeslut, värden eller maxpriser.

## Säkerhetsprincip
UI-lagret får sortera och förenkla presentationen men får inte uppgradera BEVAKA/SKIP till KÖP eller skapa nya marknadsfakta.

## QA
- Nya tester för Slutar snart, Bevaka, Research och fail-closed tomläge.
