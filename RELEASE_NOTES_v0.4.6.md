# FlipFynd v0.4.6 – Rookie & grading guardrails

## Förbättrat
- Rookie/RC-premien är nu efterfrågekänslig i stället för ett fast värdepåslag.
- Rookieetikett höjer bara confidence när spelaren är identifierad och annonsen även ger år eller identifierat set.
- Rookie på svag/okänd spelarmarknad får tydliga riskflaggor.
- Rookie påverkar även kortkvalitet och likviditet proportionellt mot spelarens efterfrågan.
- Graderade kort bedöms nu utifrån graderingsbolag, grade och spelarefterfrågan i stället för ett fast bonusvärde.
- PSA, BGS och SGC stöds med konservativa nivåer. Låga grades får liten eller ingen automatisk premie.
- PSA-titlar som `PSA GEM MT 10` tolkas korrekt som `PSA 10`.
- Svag spelarmarknad begränsar även graderingspremien.

## QA
- 29/29 unittest-tester passerar.
- Hela projektet passerar `python -m compileall -q .`.
- Ingen live-deploy eller Streamlit-verifiering har gjorts i denna release.
