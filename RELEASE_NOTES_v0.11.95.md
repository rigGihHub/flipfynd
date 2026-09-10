# FlipFynd v0.11.95 – Better Candidate Coverage

- Djupanalysen använder nu ett **diversifierat kandidatunderlag** i stället för att låta en enda rankingdominans styra alla platser.
- De ordinarie högst rankade baskandidaterna behålls alltid.
- Upp till 6 djupanalysplatser reserveras för andra befintliga signalprofiler, exempelvis:
  - rookie/prospect-signal
  - scarce/variant-signal
  - underbeskriven/research-signal
  - lågpris + relativt stark efterfrågan inom den aktuella sökningen
  - marknadsuppmärksamhet
- Lågpris/efterfrågan bedöms relativt mot aktuell kandidatpool, inte med ett nytt universellt köpgränsvärde.
- Coverage-urvalet begränsar normalt samma strukturerade spelare till högst 3 platser i det diversifierade urvalet.
- Om det saknas relevanta coverage-kandidater fylls platserna tillbaka med ordinarie adaptiva kandidater.
- Finding Funnel visar när urvalet faktiskt har breddats.
- v0.11.94:s automatiska andra analysvarv finns kvar.
- Ingen KÖP-, värderings-, maxpris-, ranking- eller risktröskel ändras.
