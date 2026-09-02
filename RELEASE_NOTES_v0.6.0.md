# FlipFynd v0.6.0 – Fyndsäker rankning

- Fyndsäkerheten påverkar nu själva rankningen, inte bara presentationen.
- Ett något mindre lönsamt men väl underbyggt fynd kan rankas över ett teoretiskt större men osäkert fynd.
- Full analys använder den kompletta Fyndsäkerheten inklusive comp-kvalitet.
- Snabbanalysen använder endast tillgänglig annons-, spelar- och kortidentitet, så kandidater inte straffas för comps som ännu inte hunnit analyseras.
- `base_rank_score` sparas separat från den säkerhetsjusterade `rank_score` för transparens och felsökning.
- Full analys visar att rankningen vägs med fyndsäkerheten.
