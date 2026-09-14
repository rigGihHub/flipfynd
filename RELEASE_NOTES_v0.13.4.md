# FlipFynd v0.13.4

- Tar bort den största CPU-upprepningen i Hitta fynd: samma marknadstitel parsas nu en gång och återanvänds i alla comp-jämförelser.
- Behåller samma djupanalys, urval, KÖP-regler och comp-krav; prestandavinsten kommer inte från att färre kort granskas.
- Cacheposter är isolerade från analysresultaten så en analys inte kan förändra en senare jämförelse.
