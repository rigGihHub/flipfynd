# FlipFynd v0.11.92 – Estimated Market Value Everywhere

- Varje synligt annons-/resultatkort visar nu **Uppskattat marknadsvärde**.
- Marknadsvärdet bygger på FlipFynds befintliga `expected_resale` och skapar ingen ny värderingsmodell.
- Om befintlig värdering inte är säker att visa anges **Otillräckligt underlag**.
- Marknadsvärde visas i:
  - huvudkortet för KÖP
  - Bästa tillgängliga
  - Slutar snart
  - Bevaka
  - Research
  - fördjupad bästa-köp-vy
  - fulla resultat-/annonskorten
- Fulla resultatkort använder ett tydligt punktestimat för marknadsvärdet; dokumenterade floor/best-case-scenarier finns kvar i fördjupningen.
- Ingen köp-, ranking-, maxpris- eller värderingslogik ändras.
