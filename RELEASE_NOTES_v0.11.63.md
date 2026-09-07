# FlipFynd v0.11.63 – Comp Set Consistency

- Comp Quality Guard räknar nu oberoende försäljningsobservationer i stället för råa Exact-rader.
- Samma försäljning kollapsas säkert via explicit sale/listing-ID eller kanonisk annons-URL.
- Cross-source/mirror-dubbletter kollapsas bara när exakt identitet, datum, pris, säljare och titel sammanfaller.
- Pris + datum ensamt räcker aldrig för deduplicering.
- Om tre Exact-rader i praktiken bara är två oberoende försäljningar blir underlaget fortsatt `THIN`.
- UI visar rått Exact-antal → oberoende försäljningar efter deduplicering.
- Samma kontroll gäller premium-comps.
- Inga värderingsvikter, prisregler eller KÖP-beslut ändras.
