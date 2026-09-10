# FlipFynd v0.12.02 – Numeric Downside Risk

- Den gamla låg/medel/hög-indelningen för kapitalrisk i Top Buy Queue är borttagen.
- De tidigare gränserna 10 % och 25 % saknade empirisk kalibrering och ska därför inte presenteras som sanning.
- FlipFynd visar i stället den faktiska beräknade **kapitalnedsidan i svagt scenario (%)**.
- `risk_band` behålls endast som kompatibilitetsfält men är nu `None`, med `risk_band_supported=False`.
- UI förklarar uttryckligen att risk visas numeriskt och att låg/medel/hög inte används utan empiriskt stöd.
- Befintliga svagt/troligt/starkt-scenarier är oförändrade.
- Ingen KÖP-, värderings-, ranking-, maxpris- eller riskmodell ändras; bara den ogrundade kategorietiketten tas bort.
