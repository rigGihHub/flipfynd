# FlipFynd v0.11.49 – Holdout Validation

- Delar deterministiskt segmentets verkliga avslut i discovery och holdout.
- Korrigeringen skattas endast på discovery-delen.
- Effekten mäts endast på holdout-delen.
- Minst 5 discovery + 5 holdout krävs.
- Minst 5 % lägre typiskt prognosfel krävs på holdout.
- Alla testade mått måste förbättras.
- Ingen produktionsmodell, ranking eller köpstatus ändras automatiskt.
