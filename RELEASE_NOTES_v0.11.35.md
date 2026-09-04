# FlipFynd v0.11.35 – Decision Confidence Audit

## Varför
Ett högt fyndscore eller stor beräknad marginal får inte ensam bära ett tydligt KÖP-beslut när värdering, identitet eller annonsunderlag fortfarande är tunt.

## Nytt
- Ny central `Decision Confidence Audit`.
- Ett KÖP kan nu sänkas till KANSKE när stöddata inte är beslutsstark.
- Granskningen tittar bland annat på värderingssäkerhet, identitet, fyndsäkerhet, annonskvalitet, risk, player-ID och comp-typ.
- Heuristic-only värdering med låg värderingssäkerhet kan inte längre tyst bära ett tydligt KÖP.
- Aktiva annonser måste ha starkare underlag än verifierade sålda comps för att få bära ett tydligt köpbeslut.
- Max köppris blockeras när prisunderlaget är för tunt.
- Full analys visar blockerare, varningar och styrkor bakom audit-beslutet.
- Audit kan aldrig uppgradera KANSKE/SKIP till KÖP och ändrar inga modellvikter.

## Säkerhetsprincip
Det är bättre att ett verkligt fynd tillfälligt hamnar i KANSKE än att FlipFynd ger ett klart KÖP på ett osäkert värde.
