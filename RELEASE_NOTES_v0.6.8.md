# FlipFynd v0.6.8 – Värderingssäkerhet & marknadskunskap

## Main improvement
Introduces a separate 0–100 valuation-confidence model. It measures how trustworthy the monetary estimate is, independently of overall deal confidence.

Inputs:
- sold vs asking-price basis
- number of usable comps
- median card-match quality
- sold-comp recency
- price dispersion
- pressure from rejected incompatible comps

Guardrails:
- asking-only evidence is capped at 55/100
- no usable comps = very low confidence
- weak comp evidence can cap total analysis confidence
- price variance and many rejected variants reduce valuation confidence

## Card-market knowledge research
Adds `data/card_market_knowledge.json` and `src/card_market_knowledge.py`.
The curated reference contains official product-structure/chase signals for hockey and football. It deliberately contains no price multipliers and cannot create a market value.

New/expanded recognition includes Topps Chrome Sapphire, Donruss Optic and Metal Universe, plus named chase/rarity signals such as Future Watch Autographs, The Cup Rookie Auto Patch, Helix, Munich at Night, Budapest at Night, Marks of Excellence, Downtown, Color Blast and Manga.

## UI
- Visible version v0.6.8
- Valuation confidence displayed separately from Fyndsäkerhet
- Explanation expander for why valuation confidence is high/low
- Curated market-knowledge signals shown with an explicit warning that they do not establish market value

## Cache
Analysis cache model bumped so previous v0.6.7 valuation results are not silently reused.

## QA actually run
- `python -m compileall -q .`: passed
- `python -m unittest discover -s tests -v`: 130/130 passed
- separate smoke check: recent matching sold comps produced sold basis and high valuation confidence; Young Guns knowledge signal was detected

No live Streamlit/Tradera verification was performed.
