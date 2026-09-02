# FlipFynd v0.10.8 – Detail Evidence Fusion

## Syfte
Göra kortidentifieringen säkrare genom att hålla isär och sedan jämföra evidens från flera källor i samma annons.

## Evidenskällor
- titel
- kategori-/annonsrad (`raw_text`)
- full detaljbeskrivning från Tradera-annonsen
- frivillig bildanalys från Visual Card Detective

## Grundregler
Titel och detaljtext blandas inte ihop till en enda osynlig textmassa i denna kontroll. Varje identitetsfält behåller sin källa. Samma uppgift från flera oberoende källor ger fler-källestöd. Motsägande kortnummer, variant eller serienämnare blir en explicit konflikt.

Bildanalys är fortfarande en hypoteskälla. Den kan stärka eller motsäga textbevis men får inte ensam skapa verifierad identitet, marknadsvärde, vinst, ROI, maxbud eller köpbeslut.

## Hunter-säkerhet
Mispriced Rookie Hunter och Misclassified Card Hunter får en extra spärr: om Evidence Fusion hittar konflikt mellan evidenskällor kapas hunter-signalen tills identiteten verifierats manuellt.
