# FlipFynd v0.6.3 – evidensbaserad kortidentifiering

## Varför denna ändring prioriterades
Genomgången av v0.6.2 visar att kortidentifieringen i huvudsak byggde på annonsrubriken. `raw_text` användes för bland annat lot-detektion och försäljningsform, men inte systematiskt för kortets set, säsong, kortnummer och variant. Det gjorde att en dåligt skriven rubrik kunde ge onödigt låg identifiering trots att samma annonsrad innehöll mer information.

## Ändrat
- Kortidentitet byggs nu av rubriken plus säker kompletterande information från Tradera-annonsens inlästa text.
- Rubriken är fortfarande primär källa. Extra annonsinformation får fylla luckor men får aldrig tyst skriva över motstridig information.
- Motstridiga fält sparas som `identity_conflicts` och blockerar tydligt köpbeslut.
- Källor per identitetsfält sparas i `identity_evidence_sources`.
- Fält som kompletterats från annonsinformationen sparas i `identity_enriched_fields`.
- Ny konservativ `card_identity_confidence_score` 0–100 visas i UI som `Kortidentifiering: X/100`.
- Vid konflikt visas varning om manuell kontroll.

## Inte ändrat
- Ingen bildanalys är införd ännu.
- Ingen extern sold-comps-källa är införd ännu.
- Lokala Tradera-comps är fortfarande aktiva annonser och behandlas fortsatt konservativt.
