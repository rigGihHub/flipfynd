# FlipFynd v0.12.59 – In-Flow Full Analysis for Seller Shortlist

## Nytt
- Live-shortlisten hos samma säljare har nu en **🔬 Fullanalysera**-knapp per kandidat.
- Knappen kör kortet genom FlipFynds vanliga fulla analyskedja i samma samfraktsvy.
- Fullanalysen visar beslut, identitetspoäng, SOLD-underlag, värderingssäkerhet, kostnad och maxpris när dessa finns.
- Resultatet matas tillbaka till samma-säljare-vyn så add-on- och korglogiken kan använda det starkare underlaget.

## Säkerhetsprincip
- Den nya knappen skapar ingen separat eller svagare köpmodell.
- Ett livekort kan endast bli KÖP-KANDIDAT om den befintliga fullanalysen faktiskt ger KÖP.
- Samfrakt får fortfarande inte skapa ett fynd på egen hand.
