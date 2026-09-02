# FlipFynd v0.11.0 – Retro UI + cache crash fix

## Fixat fel från Streamlit Cloud
Felet `AttributeError` vid `get_data.clear()` berodde på att `get_data()` inte längre var en Streamlit-cachefunktion trots att appen fortfarande anropade `.clear()` på den. `get_data()` och `get_sold_comp_data()` är nu åter `@st.cache_data`, vilket gör befintlig cache-rensning giltig och återställer avsedd uppdateringslogik efter hämtning/import/rensning.

## Ny visuell riktning: samlarkortsretro
- Ny retroinspirerad topp med varm cream, orange, guld och teal mot mörk bakgrund.
- Diskret rutnätsbakgrund som ger katalog/arkad-känsla utan att störa läsbarheten.
- Tydligare kantlinjer, offset-skuggor och mindre rundade komponenter.
- Primärknappar får fysisk "tryckknapp"-känsla.
- Onboardingkortet för Tradera-data har fått tydligare retrostatus-kort-look.
- Versionsraden visas som monospace/statusremsa.

## QA
- `python -m compileall` passerar.
- `PYTHONPATH=. pytest -q`: 263/263 tester passerar.
- Liveversionen mot Streamlit Cloud är inte verifierad i denna miljö.
