# FlipFynd v0.4.8 – Automatisk Tradera-genomsökning

## Förändringar
- Antal sidor behöver inte längre väljas manuellt.
- Smart uppdatering börjar alltid på sida 1 för att fånga nya annonser och stoppar efter tre hela sidor utan nya objekt.
- Full genomsökning fortsätter tills Tradera inte visar fler annonser, en resultatsida upprepas eller säkerhetsgränsen 250 sidor nås.
- Dubbletter inom en körning och mot redan sparade annonser identifieras.
- Hämtningen stoppar vid navigeringsfel i stället för att tyst hoppa vidare genom många sidor.
- Hämtstatus sparar senast uppdaterad tid, antal lästa sidor, antal nya annonser och stopporsak.
- Startsidan visar antal annonser i analysunderlaget och senaste uppdateringstid.
- Administrationsvyn är förenklad: inget val av sidantal behövs.

## Säkerhet
Full genomsökning har en hård säkerhetsgräns på 250 sidor för att undvika okontrollerad körning.
