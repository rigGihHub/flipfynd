# FlipFynd v0.5.8 – Annonskvalitet & identitetsguardrails

## Nytt
- Ny annonskvalitetsbedömning (0–100, låg/medel/hög) som mäter hur väl annonstexten stödjer kortidentiteten som värderingen bygger på.
- Vaga formuleringar som "se bild", "vet ej" och "okänd" sänker kvaliteten.
- Saknat set/program, år/säsong och checklistnummer hanteras som osäkerhet i stället för att modellen låtsas veta exakt kort.
- Variant/premiumegenskap utan tillräcklig produktidentitet ger tydlig identitetsrisk.
- Låg annonskvalitet kan fortfarande vara ett intressant fynd, men får inte bli ett tydligt KÖP om kortidentiteten är för osäker.
- Max köppris visas inte när identiteten bakom värderingen är för osäker.
- Extrem prisavvikelse mot det egna förväntade värdet flaggas för manuell verifiering, särskilt när annonskvaliteten inte är hög.
- Annonskvalitet visas i den fulla analysen i gränssnittet.
- Synligt versionsnummer uppdaterat till v0.5.8.

## QA
- `python -m compileall -q .` godkänd.
- `python -m unittest discover -s tests -v`: 73/73 tester godkända.
- Ingen live-verifiering mot Tradera eller Streamlit är gjord i denna release.
