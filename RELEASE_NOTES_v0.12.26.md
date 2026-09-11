# FlipFynd v0.12.26 – Market Segment Coverage

- Ny `segment_discovery_coverage.py` breddar den dyra fullanalysen över fler delar av marknaden.
- Segment definieras av tre observerbara dimensioner: budgetrelativ prisnivå, annonsform och single/lot.
- Prisnivåerna återanvänder samma budgetlogik som tidigare: micro, low, mid och upper.
- Annonsform delas i buy-now, auction och unknown utan att gissa när annonsdata är otydlig.
- Single och lot/paket hålls isär.
- Efter Budget Discovery Coverage kan upp till sex extra kandidater väljas från segmentkombinationer som ännu saknas i fullanalysen.
- Mid/upper-segment prioriteras före mer micro-brus när ett nytt segment behöver täckas.
- Max två fullanalyskandidater per spelare i segmentfasen.
- Första fullanalysens hard cap blir 42; hela andra-passkedjans hard cap blir 48.
- Detta ändrar inte deal score, värdering, risk, maxpris eller KÖP. Det ändrar bara vilka redan hämtade annonser som får full analys.
