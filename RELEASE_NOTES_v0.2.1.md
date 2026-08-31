# FlipFynd v0.2.1 – Streamlit Cloud Browser Fix

## Ändrat
- Lagt till `packages.txt` med Debian-paketet `chromium` för Streamlit Community Cloud.
- Tradera-hämtaren hittar automatiskt systeminstallerad Chromium på Linux.
- Playwright använder system-Chromium när den finns, annars sin vanliga browser lokalt.
- Lagt till `--no-sandbox` och `--disable-dev-shm-usage` för stabilare körning i container/cloud.
- Tydligare felmeddelande om Chromium ändå saknas.

## Verifierat här
- Alla Python-filer kompilerar utan syntaxfel.
- Hjälpfunktionen för Chromium-sökväg fungerar när en browser finns på PATH.

## Behöver verifieras efter push
- Att Streamlit gör full redeploy och installerar `chromium` från `packages.txt`.
- Att knappen Hämta annonser kan öppna Tradera i Streamlit Cloud.
