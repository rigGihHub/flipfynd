# FlipFynd v0.12.47 – Pull Frequency Context Engine

## Fokus
Gör publicerade odds begripliga i pack-, box- och case-kontext utan att hitta på produktkonfiguration.

## Nytt
- Ny `pull_frequency_context` som tolkar odds som `1:144 Hobby`, `1 per box` och `1 per 2 cases`.
- När `packs_per_box` och `boxes_per_case` finns explicit i kunskapsbasen räknas packodds om till ungefärlig box-/case-frekvens.
- När produktkonfiguration saknas visas endast känd packfrekvens. Ingen box/case-kontext gissas.
- `checklist_collectible_hierarchy` och `rarity_evidence` exponerar nu `frequency_band`, box-/case-ekvivalenter och om produktkonfigurationen är komplett.
- Frekvenskontext är analysstöd och får inte ensam skapa marknadsvärde eller KÖP-signal.

## QA
Nya regressionstester täcker packodds, direkt box/case-språk, konvertering med verifierad produktkonfiguration och fail-safe-beteende när konfiguration saknas.
