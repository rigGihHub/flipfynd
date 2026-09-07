# FlipFynd v0.11.76 – Portfolio Downside Stress Test

- “Mina pengar” får ett deterministiskt nedsidestest för den valda köpkorgen.
- Visar hela korgens troliga nettoutfall, alla kort samtidigt på dokumenterat floor-utfall samt försämringen däremellan.
- Visar faktisk portföljförlust i kronor och som andel av bundet kapital när all-floor blir negativt.
- Kör varje kort individuellt på floor medan övriga ligger kvar på troligt utfall för att visa vilket kort som skadar korgen mest.
- Visar största kapitalposition och dess faktiska andel av valt kapital.
- Inga sannolikheter, korrelationer, VaR-modeller eller godtyckliga stressprocent hittas på.
- Stresstestet ändrar inte Top 3, portföljval, KÖP-beslut eller maxpris.
