# FlipFynd v0.11.14 – Premium Value Guard + Faster Search

## Viktigast
- Autograf-, patch/relic-, lågnumrerade och tydliga premiumvarianter får inte längre ett exakt "Realistiskt värde" från titelheuristik när verifierade sold comps saknas.
- I sådana fall visas **Otillräckligt underlag** och nettovinst/ROI visas som **Ej beräknad** i UI:t.
- Detta förhindrar att ett premiumkort ser ut att vara värderat som ett baskort bara för att marknadsdata saknas.

## Prestanda
- Billiga filter (annonsform och specialfilter) körs före kortanalysen.
- Fast-pass-analysen cachelagras per annons, sport och strategi i Streamlit-sessionen.
- När användaren bara ändrar t.ex. en checkbox återanvänds analysen i stället för att hundratals annonser analyseras om.

## Säkerhetsprincip
- Titelheuristiken kan fortfarande användas internt för prioritering, men får inte presenteras som ett realistiskt marknadspris för premiumkort utan tillräcklig verifierad försäljningsdata.
