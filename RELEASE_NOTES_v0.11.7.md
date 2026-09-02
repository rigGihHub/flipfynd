# FlipFynd v0.11.7 – Streamlit import compatibility hotfix

- Fixar startup-kraschen där `app.py` kunde få `ImportError` i importblocket från `src.tradera_fetcher`.
- Appen importerar nu fetcher-modulen som helhet och löser nyare hjälpfunktioner via ett kompatibilitetslager.
- Om Streamlit Cloud under en kort deploy-period kör `app.py` tillsammans med en äldre `tradera_fetcher.py` startar appen i ett säkert degraderat läge i stället för att krascha helt.
- När alla filer är synkade används de riktiga funktionerna precis som tidigare.
- Inga ändringar i värderings-, ranking- eller fyndlogik.
