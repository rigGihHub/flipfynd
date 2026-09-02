# FlipFynd v0.5.3 – Parallell- och variantguardrails

## Nytt
- Förbättrad identifiering av paralleller och färgvarianter.
- Kända varianter som Gold/Silver/Red Outburst, High Gloss, Clear Cut, Cracked Ice, Speckle, Mojo, Shimmer, Pulsar, Refractor, Rainbow m.fl. får en grov kvalitetsnivå.
- Vanliga färgord som red/blue/green räknas inte längre automatiskt som paralleller utan kräver variantkontext.
- `Detroit Red Wings` kan därför inte felaktigt tolkas som en Red-parallell.
- Parallellpremien skalas efter spelarens efterfrågan och får inte ensam göra en svag spelare till fynd.
- Osäkra paralleller flaggas för kontroll mot bild/checklista.

## QA
- 47/47 unittester godkända.
- `python -m compileall -q .` godkänd.
