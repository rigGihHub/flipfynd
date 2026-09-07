# FlipFynd v0.11.50 – Correction Approval Gate

- Ny manuell approval gate efter holdout-validering.
- Endast kandidater som klarat holdout kan få status REVIEW_READY / Redo att överväga.
- Visar discovery- och holdout-sample, fel före/efter samt förbättring per mått.
- Blockerar kandidater med för få holdout-utfall, misslyckade mått eller för liten förbättring.
- Statusen innebär aldrig produktionsaktivering.
- Inga automatiska modell-, ranking- eller köpbeslutsändringar.
