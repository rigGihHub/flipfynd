# FlipFynd v0.4.1 – Quality hardening

Förberedd release som fokuserar på intern kvalitet och konsekvent kostnadslogik.

## Ändringar
- Samma regel för okänd frakt används nu i både filtrering och analys: 29 kr antas försiktigt när frakten saknas.
- Ny gemensam `src/pricing.py` för kostnadsberäkning, vilket minskar risken att UI och analysmotor räknar olika.
- Resultatdetaljen förklarar när 29 kr frakt har antagits i stället för att visa `None kr`.
- Korrekt `src/__init__.py` har lagts till; den äldre `_init_.py` lämnas kvar tills en separat städrelease verifierats.
- Standardbiblioteksbaserade regressionstester har lagts till för frakt, spelarmatchning, alias, sportsärskiljning och dataintegritet.
- Versionsnummer uppdaterat till v0.4.1.

## Avsikt
Den här releasen ändrar inte köpgränser eller marknadsvärdering. Den gör underlaget mer konsekvent och lättare att vidareutveckla utan regressioner.
