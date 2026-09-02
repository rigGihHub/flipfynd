# FlipFynd v0.9.0 – Visual Edge

## Nytt
- Tradera-crawlern fångar nu annonsbilder och alt-/bildmetadata när det finns tillgängligt.
- Ny **Visual Edge** prioriterar annonser där bildkontroll sannolikt ger mest informationsvärde.
- Bilder visas direkt i resultatkorten och i en separat Visual Edge-kö.
- Visual Edge kombinerar låg annonskvalitet, svag textidentifiering, Hidden Find, Edge Engine och chase-/raritetssignaler för att avgöra vilka bilder som bör granskas först.
- Bildmetadata kan markera att rubriken saknar viktiga kortdetaljer.

## Säkerhetsprincip
v0.9.0 gör **inte** pixelbaserad automatisk kortidentifiering. En bild eller bildmetadata får aldrig ensam skapa parallel, numrering, rookie-status, autograph/relic, marknadsvärde, ROI, vinst eller maxbud. När textunderlaget är otillräckligt visas istället att visuell verifiering krävs.

## Arkitektur
Det här är grunden för nästa steg där faktisk bildmodell kan kopplas in utan att blanda visuella hypoteser med verifierade fakta.
