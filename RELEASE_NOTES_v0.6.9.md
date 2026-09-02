# FlipFynd v0.6.9 – Card Knowledge Expansion

## Vad som ändrats

- Utökat `data/card_market_knowledge.json` med officiellt dokumenterade hockey- och fotbollsstrukturer.
- Ny kunskap om bland annat Young Guns High Gloss/Exclusives/Deluxe, OPC Platinum Seismic Gold/Orange Checkers/Emerald Surge, Metal Universe PMG Red/Green/Gold samt flera Topps Finest chase-/autografprogram.
- Varje kunskapssignal kan nu bära `print_run`, `attention_priority` och `source_id`.
- Ny `market_knowledge_attention()` som ger en konservativ granskningsprioritet 0–28.
- Kända sällsynta/chase-strukturer kan prioriteras till appens begränsade fullanalys-pool även om snabbpasset ännu inte kan värdera dem väl.
- Granskningsprioriteten påverkar **inte** marknadsvärde, nettovinst, ROI, maxbud eller slutlig rank direkt.
- Kortparsern känner nu igen PMG Red/Green/Gold, Emerald Surge, Orange Checkers, Seismic Gold och Violet Pixels mer exakt samt Topps Finest som produkt.
- UI visar granskningsprioritet för kända samlarsignaler och förklarar att signalen inte är prisbevis.
- Analyscacheversion höjd till `flip_v9_card_knowledge_analysis_priority`.
- Version i UI: v0.6.9.

## Varför detta förbättrar fyndkvaliteten

Ett extremt sällsynt eller viktigt kortprogram kan tidigare ha hamnat utanför de 12 objekt som får full comp-analys eftersom snabbvärderingen saknade tillräckligt underlag. v0.6.9 använder officiell produktkunskap endast för att avgöra **vad som förtjänar djupare kontroll**, inte vad det är värt.

Det minskar risken att FlipFynd missar felprissatta varianter utan att skapa falska värden.

## QA

- `python -m compileall -q .` – godkänd.
- `python -m unittest discover -s tests -p 'test_*.py'` – 138/138 tester godkända.
- Nya tester täcker Young Guns High Gloss, OPC Platinum Emerald Surge, PMG-hierarki, Topps Finest chase-program, cross-sport-skydd och nya parallel-parserregler.
- Ingen live-verifiering på Streamlit eller aktuell Tradera-data genomförd.
