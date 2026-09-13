# FlipFynd v0.12.78 – Controlled Oddity Registry Learning

## Fokus
Göra Oddity-kunskapsbasen självlärande på ett kontrollerat sätt utan att låta runtime-signaler skriva in obekräftade hobbyhistorier som fakta.

## Nytt
- Ny `src/oddity_registry_learning.py`.
- FlipFynd grupperar återkommande oddity-/variant-signaler på exakt kortidentitet och bygger **registry proposals**.
- Förslag får status `NEEDS_EVIDENCE`, `NEEDS_CORROBORATION` eller `REVIEW_READY`.
- `REVIEW_READY` kräver upprepade observationer, stark identitet och oberoende corroboration såsom exact SOLD, checklistreferens eller verifierad bildvariant.
- Kort som redan finns i det kuraterade registret filtreras bort.
- Ny UI-sektion **Förslag till Oddity-kunskapsbas – kräver granskning**.

## Säkerhetsprincip
Runtime får aldrig själv ändra `CURATED_ODDITY_CARDS`. Ett förslag skapar inte marknadsvärde, SOLD-comp eller KÖP. En människa/developer måste granska källorna och manuellt skapa en ny kuraterad post.
