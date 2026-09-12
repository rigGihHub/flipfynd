# FlipFynd v0.12.63 – Near-Unlock Research Prioritisation

## Fokus
Sluta forska på hundratals kort samtidigt när comp-data är flaskhalsen. Prioritera i stället de kandidater där minsta nästa evidenssteg sannolikt låser upp mest beslutsunderlag.

## Nytt
- Ny `src/unlock_research_queue.py`.
- Högsta prioritet: exact-ID-kort med exakt 1 verifierad SOLD – **1 sale från comp-tröskeln**.
- Därefter: exact-ID-kort utan sales, följt av kort där SOLD finns men värdering/maxpris ännu saknas.
- Spelarstatus och samlarprestige kan inte kompensera för svag evidens; `deal_score` används bara som tie-breaker inom samma researchnivå.
- Researchkön diversifierar spelare när det finns alternativ.
- Ny UI-sektion **⚡ Närmast att låsa upp – research med högst hävstång**.
- Den bredare “mest lovande”-researchlistan finns kvar men är nedfälld som sekundär vy.

## Säkerhetsprincip
Researchprioritet är inte ett köpbeslut. Funktionen skapar aldrig marknadsvärde, maxpris eller KÖP.
