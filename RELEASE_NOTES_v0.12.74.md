# FlipFynd v0.12.74 – Verification Priority Queue

## Fokus
När candidate matchern hittar flera möjliga comp-träffar ska FlipFynd lägga verifieringstid på rätt träffar först.

## Nytt
- Ny `research_verification_priority.py` väljer de starkaste konfliktfria kandidatmatcherna för full verifiering.
- Kandidater som uttryckligen uppges vara SOLD får högre researchprioritet, men SOLD-claim blir **aldrig** automatiskt SOLD-evidens.
- Kön försöker sprida de första verifieringarna över oberoende källor i stället för fem nästan identiska träffar från samma marknadsplats.
- Ny UI-sektion **Verifiera dessa träffar först** i den automatiska comp-jakten.
- Hårda konflikter (fel parallel/version m.m.) hålls utanför verifieringskön.

## Säkerhetsprincip
Prioritering är inte verifiering. Funktionen skapar aldrig exact identity, exact SOLD, värdering, maxpris eller KÖP.
