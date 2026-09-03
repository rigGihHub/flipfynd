# FlipFynd v0.11.16 — Exact Premium Valuation Range

- Ny modul `src/premium_valuation.py`.
- Premiumkort med minst två exakta premium-sold comps får ett observerat låg/bas/hög-intervall.
- Färskare försäljningar väger tyngre i basvärdet.
- Premiumkortets ekonomiska analys använder det exakta premium-basvärdet när säkerhetskraven är uppfyllda, i stället för bred same-player-comp/heuristik.
- UI visar spridning, antal färska avslut och intervallsäkerhet.
- Cachemodell höjd till `flip_v26_exact_premium_valuation`.
