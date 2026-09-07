# FlipFynd v0.11.48 – Evidence-Based Correction Simulator

- Simulerar modellkorrigeringskandidater mot verkliga Flip Journal-utfall.
- Korrigeringen baseras på segmentets observerade medianfel.
- Visar typiskt absolut prognosfel före och efter simuleringen.
- Minst 5 jämförbara utfall krävs per mått.
- Minst 5 % förbättring och lägre fel krävs för att ett mått ska klara filtret.
- Alla testade mått för kandidaten måste förbättras för att kandidaten ska gå vidare.
- Samma historiska data används både för att upptäcka och simulera korrigeringen, därför är detta endast ett första filter och inte out-of-sample-bevis.
- Inga automatiska modell-, ranking- eller köpbeslutsändringar.
