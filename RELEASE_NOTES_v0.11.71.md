# FlipFynd v0.11.71 – Heuristic Integrity

- Buy Now vs Wait ersätts av deskriptiva statusar: `INOM MAXPRIS`, `ÖVER MAXPRIS`, `BEVAKA`.
- Tar bort 90%-regeln, risk <65 och confidence >=50 som timingtrösklar.
- Prisfallsmål använder exakt befintligt maxpris; ingen påhittad 10%-buffert.
- Opportunity Gap visar endast exakt kr/%-avstånd till maxpris; inga 10/25/50-kronorsband.
- Watch Priority saknar syntetisk score, CE-/ROI-vikter och 75/55-gränser.
- Bevakningsordning = närmast faktiskt maxpris först.
- Inga nya KÖP-beslut, värderingsändringar eller automatiska modelländringar.
