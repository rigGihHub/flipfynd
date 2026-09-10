# FlipFynd v0.12.03 – Discovery Engine 2.0 Foundation

- Ny `discovery_engine.py` samlar befintliga fyndsignaler i tydliga discovery-spår utan att skapa en ny magisk score.
- Discovery-spår omfattar bl.a. hidden find, dålig/felklassad annons, rookie/prospect, variant/scarcity, lågpris, lågpris+demand, ending soon, buy now, lot research och market attention när motsvarande befintliga signal finns.
- Om första djupanalysen ger 0 KÖP får upp till 10 utelämnade kandidater från olika discovery-spår förtur till befintlig full analys.
- Urvalet prioriterar nya discovery-profiler och spelardiversitet, därefter befintlig `rank_score`.
- Kandidater utan discovery-signal får ingen påhittad sådan.
- Därefter kan befintliga Find More Cards fylla återstående analysutrymme.
- Totalt hard cap för andra analysvarvet är fortsatt 45.
- KÖP-krav, värdering, sold-krav, maxpris, risk och slutlig ranking ändras inte.
- Funnel-diagnostiken visar när Discovery Engine faktiskt gav fler fyndspår djupanalys.
