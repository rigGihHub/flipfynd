# FlipFynd v0.13.7

- Korrigerar Traderas profilsidformat vid återupptagen sökning: `s`-värdet är säljarens totala annonsmängd, inte sidstorleken.
- Etanol71 sida 4 byggs därför som `paging=4.a0.s9013` i stället för den felaktiga `paging=4.a0.s48`.
- Det sparade totalantalet återanvänds efter omstart, så sökningen kan fortsätta förbi de första 240 annonserna.
