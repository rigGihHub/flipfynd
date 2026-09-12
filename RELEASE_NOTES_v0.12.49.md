# FlipFynd v0.12.49 – Observed Identity Fusion

## Fokus
Fixar identitetsrutan som kunde visa “Ej säkert identifierat” trots att Top-3-annonsens titel redan innehöll spelare, set, säsong och kortnummer.

## Nytt
- Top-3-rader behåller nu originalets fulla analysobjekt för drill-down/förklaringar.
- Identitetsrutan skiljer på **observerat från annonstitel**, **strukturerat/tolkat** och **verifierat**.
- Titeldata får visas som observation utan att låsa upp exact-comp-gaten.
- Stöd för **Upper Deck Collector's Choice** som specifikt set i parsern.
- UI visar källa per identitetsfält och använder inte längre “Ej säkert identifierat” som synonym för “inte verifierat”.

## Säkerhetsprincip
Observerat är inte verifierat. Exact comps och beslutsstöd fortsätter kräva Exact Identity Gate.
