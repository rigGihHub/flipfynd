# FlipFynd v0.4.0 – Smartare fyndmotor

## Förändringar
- Spelarnas market score ligger nu i `data/player_market.json` i stället för hårdkodat i analysmotorn.
- Gemensam, accent-insensitiv spelarmatchning för hockey och fotboll.
- Försiktig stavningstolerans för fullständiga spelarnamn; osäkra träffar blir hellre okända än felidentifierade.
- Utökad spelardata för både hockey och fotboll.
- Fotbollsset identifieras nu bättre i parsern.
- Fotboll får lokal comp-analys med enbart fotbollsdata, i stället för att alltid sakna comps.
- Okända/osäkra spelare får lägre marknadsscore och kan inte få ett tydligt KÖP-beslut utan tillräcklig analyssäkerhet.
- Ranking väger nu in ROI tydligare och begränsar hur mycket en stor nominell vinst ensam kan dominera rankingen.
- Resultatkorten visar varning vid osäker eller fuzzy spelaridentifiering.
- Versionsnummer uppdaterat till v0.4.0.

## Avsikt
Release 0.4.0 prioriterar träffsäkerhet och verklig flip-potential framför fler funktioner. Den är medvetet konservativ när spelaridentiteten är osäker.
