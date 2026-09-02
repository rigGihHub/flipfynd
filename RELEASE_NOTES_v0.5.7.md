# FlipFynd v0.5.7 – Lot- och duplikatskydd

## Nytt
- Konservativ lot-detektering för annonser med flera kort, inklusive explicit antal som `5 kort`, `lot 5`, `bundle`, `kortpaket` och samlingsannonser.
- Officiella setnamn som `Ultimate Collection` och `Museum Collection` feltolkas inte längre automatiskt som lot/samling.
- Lot-status kan hämtas även från Tradera-annonsens omgivande text, inte bara rubriken.
- Flerkortsannonser kan inte längre bli ett tydligt KÖP baserat på en single-card-värdering.
- Max köppris/budtak döljs för lot-annonser eftersom styckvärdet inte är verifierat.
- Comp-analysen deduplicerar sannolika återlistningar från samma säljare med samma kortidentitet och nästan samma pris.
- Nästan identiska annonser från olika säljare behålls som separata marknadssignaler.
- Analysresultatet exponerar `is_lot`, `lot_count` och `lot_confidence`.

## QA
- 68/68 unittester godkända.
- `python -m compileall -q .` godkänd.
- Ingen live-verifiering mot Tradera eller Streamlit har gjorts för denna release.
