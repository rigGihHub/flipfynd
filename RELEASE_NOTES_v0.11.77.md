# FlipFynd v0.11.77 – Portfolio Opportunity Cost

- “Mina pengar” visar nu opportunity cost mot faktiska verifierade alternativa portföljer.
- Visar hur många kr/30 dagar som offras om användaren väljer en långsammare verifierad kombination.
- Identifierar kortet i vald korg med lägst verifierad vinsttakt per 100 kr bundet kapital.
- Kvarvarande kontanter får ingen antagen avkastning.
- Om ingen verifierad KÖP-kandidat ryms i reservkapitalet säger appen uttryckligen att kontanter kan lämnas oanvända.
- Om en verifierad icke-vald kandidat faktiskt ryms i reservkapitalet flaggas detta som granskningssignal för sökpool/max_cards, inte som automatiskt köp.
- Inga framtida fynd, sannolikheter eller syntetiska opportunity-cost-räntor modelleras.
- Portföljranking, KÖP-beslut och maxpris ändras inte.
