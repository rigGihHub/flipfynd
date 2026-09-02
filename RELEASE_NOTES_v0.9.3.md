# FlipFynd v0.9.3 – Exact Comp Hunter

- Lägger till `src/exact_comp_hunter.py`.
- En exact-comp-sökning låses upp först när Visual Card Detective har en kandidat med oberoende identitetsstöd.
- Bygger smala söksträngar från spelare, säsong, set, kortnummer, parallel, serial, auto/patch och grading.
- Klassificerar lokal historik i EXACT, NEAR, WEAK och REJECTED.
- Kortnummer-, säsongs-, serial-, grade- och parallelkonflikter får inte smyga in som exakta comps.
- Endast poster med explicit sold-evidens räknas som exakt såld comp.
- Skapar direkta söklänkar till Tradera och eBay sold för manuell verifiering.
- Exact Comp Hunter ändrar inte värdering eller köpbeslut automatiskt.
- Kvalitetsfix: riskmodellens spridningsanalys accepterar nu `price` som fallback när comparable-detail saknar `total_price`.
