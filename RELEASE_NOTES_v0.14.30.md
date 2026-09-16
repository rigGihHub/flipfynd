# FlipFynd v0.14.30 – striktare prisunderlag och korrekt djupanalys

Tre separata specialistgranskningar av identifiering, ekonomiskt underlag och
säljsökning reproducerade fel i den ordinarie analyskedjan. Detta är rättningar
av befintlig analyslogik, inte nya påståenden om kortvärden.

## Förändringar

- Graderade jämförelsepriser kräver överensstämmande graderingsuppgifter.
  PSA 10-priser får inte användas för ett kort utan sådan gradingevidens.
  Bolag, betyg och motsägelser mellan titel och strukturerade uppgifter kontrolleras.
- Externa generiska exporter med enbart `completed` blir inte automatiskt SOLD.
  Generiska prisfält kräver uttrycklig såld-status eller såld-flagga. Motstridiga
  statusfält kan inte döljas av en tidigare positiv uppgift.
- En lyckad djupanalys får inte ersättas med samma annons äldre snabbbedömning
  när djupanalysen sorterar bort kortet. Reservvisning finns kvar för misslyckad
  eller ännu inte genomförd djupanalys.
- KÖP-krav, verifierad ekonomi och åtskillnaden mellan aktiva priser och SOLD
  bibehålls. Signaler om korttyp skapar aldrig värde ensamma.

## Primärkällor kontrollerade 2026-09-16

- [PSA Grading Standards](https://www.psacard.com/gradingstandards) – grading
  beskriver bedömt kortskick; ett ograderat kort får inget antaget PSA-betyg.
- [eBay Advanced Search](https://www.ebay.com/sch/ebayadvsearch) – Completed items
  och Sold items är separata filter. Export utan tydligt källschema behandlas konservativt.

## Verifiering

Regressionstester täcker både blockerade felaktiga underlag och fortsatt stöd
för matchande graderingar, explicita försäljningar och legitim reservvisning.
Hela testsviten och syntaxkontrollen körs före publicering. Git-blobbar och
hela kodträdet jämförs med den testade versionen innan main uppdateras.

Resultat: 1 392 tester godkända (61 nya testfall); syntaxkontroll godkänd.

## Nästa identifierade förbättringar (inte ändrade här)

- Bevara strukturerade identitetsfält genom hela kedjan för exakta premiumjämförelser.
- Överföra fullanalysens riskpoäng till säljsökningens kompakta presentationsunderlag.
