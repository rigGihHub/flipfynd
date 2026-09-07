# FlipFynd v0.11.39 – Model Review Dashboard

## Syfte
Samla verkliga utfall i en enda manuell modellgranskning innan några viktförändringar ens övervägs.

## Nytt
- Ny `Model Review` i Flip Journal.
- Kombinerar False Positive Review och False Negative Review.
- Visar utfall per ursprungligt beslut: KÖP, KANSKE och AVSTÅ.
- Visar andel lönsamma avslut och median faktisk nettovinst per beslut.
- Jämför signaler som både kan ge dåliga KÖP och missade starka vinnare.
- Minst 5 relevanta avslut krävs innan ett signalmönster visas.
- Minst 20 verkliga avslut krävs innan dashboarden säger att manuell modellgranskning har rimligt underlag.
- Ingen automatisk viktändring, rankingändring eller beslutspåverkan.

## Viktig tolkning
En signal kan förekomma både i dåliga KÖP och i missade vinnare. Dashboarden sätter därför inte förenklade gröna/röda betyg på signaler och påstår inte kausalitet.

## QA
Se verifierad testrapport för releasen.
