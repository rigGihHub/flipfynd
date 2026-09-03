# FlipFynd v0.11.17 — Smart Sold Comp Acquisition

- Smart lokal källskanning för verifierbara avslut från kända FlipFynd-JSON-källor.
- Collector fortsätter att vägra tolka `ended`, `closed` eller ett vanligt aktivt pris som såld försäljning.
- Varje accepterad comp märks med `sold_verification_status`, `sale_evidence_type` och `acquisition_source`.
- Ny avvisningsdiagnostik visar varför rader inte får bli sold comps.
- UI har en tydligare `Smart Sold Comp Acquisition`-panel med källdiagnostik.
- Manuell import får samma verifieringsmetadata som collector-flödet.
- Ingen ny extern scrapingkälla introduceras i denna release; säker evidens går före täckning.
