# FlipFynd v0.14.29

## Rättad start efter publicering

- Rättar ett syntaxfel i den publicerade v0.14.28: en bokstavlig radbrytningssekvens i signalernas UI-etiketter gjorde att app.py inte kunde kompileras.
- Ett nytt regressionstest kompilerar hela Streamlit-entrypointen inom den vanliga pytest-sviten, utan att starta appen eller göra nätverksanrop.
- Testet reproducerade felet på v0.14.28 före rättningen.
- Vid publicering jämförs uppladdade Git-blobbar och hela Git-trädet med den lokalt testade versionen innan main uppdateras. Ingen separat omskrivning av app.py vid uppladdning.
- Inga ändringar i ranking, värdering, SOLD-krav eller KÖP-gränser.
