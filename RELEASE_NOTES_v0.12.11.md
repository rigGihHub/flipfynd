# FlipFynd v0.12.11 – Market Gap Hunter 2.0

- Ny researchmotor för tunt aktivt utbud relativt befintlig efterfrågesignal.
- Utbud mäts endast i aktuell analyserad kandidatpool och på strukturerat `player_name`; det påstås inte vara hela marknaden.
- 1–2 aktiva kandidater räknas som tunt utbud för research. Tre eller fler gör inte det.
- Positiv befintlig `player_card_demand_score` krävs för att skapa en Market Gap-kandidat.
- `GAP_WITH_MARKET_EVIDENCE` kräver dessutom minst två matchande sold comps och `valuation_display_safe=True`.
- Annars stannar signalen vid `GAP_RESEARCH_ONLY` med tydliga blockers.
- Market Gap skapar aldrig KÖP, marknadsvärde, maxpris eller ny fyndscore.
- Ny novice-expander: **Market Gap – tunt utbud att undersöka**.
