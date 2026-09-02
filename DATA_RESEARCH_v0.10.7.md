# DATA RESEARCH v0.10.7 – Smart Listing Detail Enrichment

## Syfte

v0.10.7 gör Tradera-inläsningen selektivt djupare. Kategorisidor används fortfarande för bredd och snabbhet, men ett begränsat antal prioriterade annonser öppnas dessutom på själva objektsidan för att samla mer synlig metadata.

## Principer

- Detaljberikning är en discovery-/identitetsfunktion, inte en värderingsmotor.
- Nya annonser prioriteras före redan kända annonser.
- Kort/generisk titel, rookieprogram, auto, patch/relic, chase/SSP, serienummer och parallellstruktur höjer detaljprioriteten.
- Motorn försöker samla full beskrivning, fler bildreferenser, budantal, sluttidstext och säljartext när uppgifterna är synliga.
- Misslyckad detaljhämtning får inte stoppa den vanliga kategorihämtningen.
- Tidigare lyckad detaljmetadata bevaras vid senare kategoriuppdateringar.
- Full beskrivning får komplettera saknade identitetsfält men titeln är fortsatt auktoritativ vid konflikt.
- Bildreferenser från detaljsidan slås ihop med kategori-bilder för Visual Edge, utan att pixelinnehållet tolkas automatiskt.

## Säkerhet

Detaljprioritet och detaljmetadata får inte i sig skapa eller höja marknadsvärde, nettovinst, ROI, maxbud eller köpbeslut. De förbättrar endast underlaget för senare identifiering och verifiering.

## Teknisk begränsning

Tradera kan ändra DOM, etiketter och metadataformat. v0.10.7 använder därför flera defensiva fallbacks (JSON-LD, metadata, brödtext och bildreferenser). Selektorerna är inte live-verifierade i denna release.
