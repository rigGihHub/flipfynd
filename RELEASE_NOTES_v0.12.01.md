# FlipFynd v0.12.01 – Direct Sport Refresh

- Avancerad marknadshämtning har förenklats och gjorts konsekvent.
- Den tidigare sport-radioknappen i avancerad marknadshämtning är borttagen eftersom nästa sidblock redan hade direkta sportknappar och radion i praktiken främst styrde refresh-flödet.
- **Läs nästa sidblock** fortsätter ha två tydliga knappar:
  - 🏒 Hockey
  - ⚽ Fotboll
- **Uppdatera gamla sidor** har nu samma direkta upplägg:
  - 🏒 Uppdatera gamla sidor – Hockey
  - ⚽ Uppdatera gamla sidor – Fotboll
- Varje refresh-knapp använder sin egen freshness/due-status och är avstängd när just den sporten inte behöver uppdateras.
- Hockey och fotboll startar fortsatt separata `scheduled_refresh`-jobb med rätt Tradera-kategori.
- Onboarding-radioknappen när ingen data finns kvar oförändrad, eftersom den där faktiskt behövs för valet Hockey/Fotboll/Båda.
- Ingen fynd-, värderings-, KÖP-, maxpris- eller risklogik ändras.
