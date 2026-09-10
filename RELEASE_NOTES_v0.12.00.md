# FlipFynd v0.12.00 – Shipping Truth Fix

- Ny gemensam `shipping_truth`-modul som används som enda källa för fraktproveniens i viktiga beslutsvyer.
- Faktisk annonserad frakt vinner alltid över tidigare analysantaganden.
- **0 kr frakt** behandlas som riktig fri frakt och tappas inte längre genom Python `or`-logik.
- Om faktisk frakt saknas används befintligt försiktigt antagande, men UI märker det tydligt som **Antagen frakt**.
- Best Buy Decision Card exponerar nu `shipping_known` och `shipping_label`.
- Novice BUY-vyn och avancerad Best Buy-vy visar `Frakt` respektive `Antagen frakt`.
- Auktionsbudtak och dynamiskt maxbud använder samma gemensamma fraktkälla.
- `compute_max_purchase_price` sparar nu fraktens proveniens (`shipping_known`, `shipping_source`).
- Ingen KÖP-, värderings-, ranking- eller risktröskel ändras.
