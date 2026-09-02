# FlipFynd v0.7.3 – Dolda fynd

- Ny separat Dold fynd-signal 0–100 för annonser som kan vara svårare att hitta via normal sökning.
- Signalen tittar på generiska/korta rubriker, svag spelartext, viktig identitetsdata som bara finns i annonsinformationen, lots och svag annonskvalitet.
- Dold fynd-signalen är uttryckligen separerad från marknadsvärde, maxbud och KÖP-beslut. Dålig rubrik får aldrig skapa ett fynd av sig själv.
- Ny sektion `🕵️ Dolda fynd` i resultatvyn samt märkning på berörda resultat.
- Analyscache höjd till `flip_v12_hidden_find_signal`.
- Webbresearch inför releasen stödjer hypotesen att breda/generiska rubriker och felstavningar kan ge lägre synlighet, men FlipFynd kräver fortfarande comps innan köp rekommenderas.
