# FlipFynd v0.12.23 – Discovery & Ranking Reset

- Topp 3 är ombyggd så att fyndpotential och evidenssäkerhet aldrig blandas ihop visuellt.
- Ett kort kan ha hög **Fyndpotential** men låg **Säkerhet** och visas då som `Lovande – behöver verifieras`, inte som ett verifierat fynd.
- `Bästa verifierade fynd` kräver befintligt KÖP-beslut, minst 60/100 säkerhet, minst två verifierade SOLD, exact-identity redo och säkert visningsbart marknadsvärde.
- `Bästa av resten` används som transparent fallback när underlaget är svagt.
- Osäkra marknadsvärden döljs även om ett internt estimat finns.
- Ny Budget Discovery Coverage säkerställer att fullanalysen inte domineras av extremt billiga kort när användarens budget tillåter andra prisnivåer.
- Prisband relateras till aktuell budget: micro <=5 %, low <=20 %, mid <=50 %, upper >50 %.
- Upp till åtta extra kandidater kan fullanalyseras för budgetbredd, med max två per spelare och hard cap 38 i första analysfasen.
- Detta ändrar inte värderings-, KÖP-, maxpris-, risk- eller sold-regler. Det ändrar vilka kandidater som får chans till full analys och hur resultaten presenteras.
