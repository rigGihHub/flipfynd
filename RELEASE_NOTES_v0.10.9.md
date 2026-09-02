# FlipFynd v0.10.9 – Data onboarding & fetch recovery

- Flyttar fram Tradera-hämtningen till huvudflödet när appen saknar annonser.
- Stor primär knapp: **Hämta hockey + fotboll från Tradera**.
- Analysknappen är avstängd när datasetet är tomt, så användaren inte får ett missvisande filterfel.
- Tomt dataset förklaras som dataproblem, inte som att sökparametrarna gav noll träffar.
- Vid hämtfel visas en tydlig **Försök igen**-knapp och tekniska detaljer under en expander.
- `start_fetch()` fångar nu även fel som uppstår innan bakgrundsprocessen hunnit starta, i stället för att krascha hela Streamlit-vyn.
- När data redan finns visas en diskret **Uppdatera annonser**-knapp högst upp.
