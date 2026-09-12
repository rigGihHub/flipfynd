# FlipFynd v0.12.44 – Checklist Knowledge Pipeline

## Fokus
Göra checklist-, case-hit- och short-print-kunskap skalbar, källstyrd och auditerbar i stället för att växa som en osammanhängande lista.

## Nytt
- Ny `src/checklist_knowledge_pipeline.py`.
- Officiell käll-allowlist för Upper Deck, Topps och Panini.
- Automatisk validering av signaler, okända source IDs, ogiltiga print runs och strukturella konflikter.
- Dubblett-/konfliktdetektering per sport + produkt + program + label.
- Produktvis täckningsrapport så nästa research kan riktas mot kunskapsluckor.
- CLI: `python build_checklist_knowledge.py`.
- Kunskapsbasen utökad med fem källstyrda 2025-26 Upper Deck Series 2-strukturer:
  - Incarnations 1:1920 Hobby
  - Dazzlers Gold 1:2880 Hobby
  - UD Canvas Program of Excellence 1:864 Hobby
  - Population Count 25 /25
  - Base Young Guns 1:2 Hobby

## Princip
Packodds och print runs beskriver knapphet, inte marknadsvärde. Vanliga rookie-programodds får inte blandas ihop med sällsynta paralleller eller case-hit-påståenden.
