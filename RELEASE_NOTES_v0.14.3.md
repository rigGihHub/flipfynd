# FlipFynd v0.14.3

## Snabbare upprepade sökningar

- Ett identiskt tryck på **Hitta fynd** återanvänder nu den senast färdiga analysen i sessionen.
- Resultatet återanvänds bara när annonsdata, sålda comps, analysversion och samtliga analysfilter är oförändrade.
- Cachen håller endast en komplett körning för att undvika växande minnesanvändning.

## Mätbar analyskedja

- Diagnostiken mäter nu filtrering, snabbpass, djupanalys och total analystid separat.
- Resultatvyn visar om körningen analyserades på nytt eller hämtades direkt från cache.

## Verifiering

- 1 268 tester passerar.
