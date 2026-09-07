# FlipFynd v0.11.40 – Decision-Grade Sold Comp Intake

## Varför
Den största flaskhalsen är fortfarande riktig SOLD-data. En tidigare risk var att begreppet "verifierad sold comp" kunde uppfattas som att både försäljning och exakt kortidentitet var verifierade, trots att de är två separata frågor.

## Nytt
- nytt `sold_comp_intake`-lager som separerar verifierad försäljning från exakt kortidentitet
- fyra tydliga statusar: `EXACT_READY`, `IDENTITY_REVIEW`, `SALE_ONLY`, `REJECTED`
- en verifierad försäljning kan aldrig ensam bli `EXACT_READY`
- exakt identitet kräver strukturerade fält för spelare, set/program, säsong/år och kortnummer
- exact-ready kräver dessutom uttrycklig identitetsbekräftelse; titeltext räcker aldrig
- konflikter blockerar exact-ready
- parallel/numrering/gradering kräver relevant strukturerad metadata när raden säger att egenskapen finns
- importer bevarar nu uttrycklig identitetsmetadata utan att gissa från fritext
- nytt UI: "Exact Comp Intake" visar exakt klara comps och en prioriterad granskningskö

## Säkerhetsprincip
`EXACT_READY` betyder bara att en såld rad är tillräckligt väl identifierad för att få gå vidare till separat exact-matchning. Det betyder inte att den automatiskt matchar det kort som analyseras och det skapar aldrig ett värde eller KÖP-beslut på egen hand.

## Ingen låtsasintegration
Releasen påstår inte att eBay, 130 Point, Card Ladder eller annan extern källa har fått automatisk ingestion. Sådan åtkomst kräver en verklig, tillåten och verifierad integrationsväg.
