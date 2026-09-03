# Data research v0.11.16 — Exact Premium Valuation Range

Den här releasen använder inga nya externa prisantaganden. Premiumintervallet byggs enbart från redan importerade eller insamlade sold comps som Premium Comp Hunter klassar som `EXACT_PREMIUM`.

Regler:
- minst två exakta premiumförsäljningar med positivt pris krävs,
- låg/hög är observerade priser, inte uppskattade priser,
- basvärdet är en färskhetsvägd median,
- avslut ≤90 dagar viktas 1.00, 91–180 dagar 0.85, 181–365 dagar 0.70, äldre 0.55 och odaterade 0.65,
- inga aktiva annonser eller breda samma-spelare-comps används för premiumintervallet,
- inga valutakurser gissas i denna modul.
