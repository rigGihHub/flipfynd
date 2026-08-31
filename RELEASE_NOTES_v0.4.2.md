# FlipFynd v0.4.2 – Conservative comps

## Förbättringar
- Lokal comp-analys använder nu exakt samma konservativa fraktregel som huvudanalysen. Saknad frakt räknas alltså inte längre som 0 kr i jämförelseannonser.
- Aktiva Traderaannonser vägs mer försiktigt eftersom de är begärda priser, inte verifierade försäljningar.
- Comp-vikten styrs nu även av comp-kvalitet (låg/medel/hög), inte bara antal träffar.
- Låg comp-kvalitet höjer inte längre analysens confidence.
- Analysorsaken visar comp-kvalitet för bättre transparens.
- Nya regressionstester för kostnadskonsistens och comp-viktning.

## Version
- APP_VERSION: v0.4.2
