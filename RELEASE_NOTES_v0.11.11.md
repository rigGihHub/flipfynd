# FlipFynd v0.11.11 – Guided Fetch Lock + Ending Soon Hunter

## Nytt huvudflöde
- Tydligt fyrastegsflöde: Hämta annonser → Vänta på KLAR → Hitta fynd → Agera.
- UI visar vilket steg användaren befinner sig i just nu.
- `Hitta fynd` låses automatiskt medan en Tradera-hämtning pågår.
- Knapptexten ändras till `⏳ Vänta – annonser hämtas` under aktiv hämtning.
- När data är redo visas tydligt att `Hitta fynd` kan användas.
- Tooltip förklarar att `Hitta fynd` analyserar redan inlästa annonser och inte hämtar ny data.

## Ending Soon Hunter
- Ny sektion `⏰ Slutar snart – under säkert maxbud`.
- Endast auktioner med säkert tolkningsbar relativ sluttid kan kvalificera sig.
- Kräver befintligt säkert maxbud, minst 2 verifierade sold comps, värderingssäkerhet >=60 och godkänd Exact Identity Gate.
- Aktuellt totalpris måste fortfarande ligga under befintligt säkert maxbud.
- Identitetskonflikt och lot-annons blockerar signal.
- Motorn skapar aldrig egen sluttid, värdering eller maxbud.

## QA
- 304/304 tester passerar med `PYTHONPATH=.`.
- `compileall` passerar.
