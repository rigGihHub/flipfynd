# FlipFynd v0.11.99 – Safer Market Value & Max Price

- Ny **Valuation Evidence Gate** avgör om ett redan beräknat uppskattat marknadsvärde och Betala högst får visas som beslutsstarkt underlag.
- Grinden skapar inga nya värden och ändrar inga köpgränser.
- För vanlig kortvärdering krävs nu samtidigt:
  - sold-baserad värdering
  - minst 2 matchande verifierade sålda jämförelseobjekt
  - befintlig värderingssäkerhet på minst 60/100
  - strukturerad identitet som redan klarar Exact Identity Gates exact-comp-sökning
- Premiumkort behåller den striktare regeln om minst 2 exakta premiumförsäljningar.
- **Betala högst** döljs när samma evidensgrind inte är godkänd.
- Dynamiskt maxbud är fortfarande striktare och kräver dessutom befintlig `supports_dynamic_max_bid`.
- Heuristik eller aktiva annonser kan fortfarande användas som research/analysstöd men visas inte längre som säkert uppskattat marknadsvärde.
- UI-lager använder nu fail-closed standard: saknas `valuation_display_safe` döljs marknadsvärdet i stället för att antas vara säkert.
- När sold-biblioteket växer genom v0.11.96–0.11.98 kan fler kort automatiskt passera samma befintliga evidenskrav utan att trösklarna sänks.
