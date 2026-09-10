# FlipFynd v0.12.05 – Bad Listing Hunter 2.0

- Ny `bad_listing_hunter.py` identifierar annonser som kan vara lättare för andra köpare att missa på grund av svag annonskvalitet.
- Hunter bygger enbart på redan producerad FlipFynd-evidens: listing quality-varningar/blockerare, Hidden Find, Information Edge och befintlig spelartext-matchning.
- Signaler omfattar bland annat mycket kort titel, saknat set/program, saknat år/säsong, saknat kortnummer, vag beskrivning, ofullständig premiumidentitet, osäker spelartext och identitetskonflikt.
- Hunter får aldrig rätta ett stavfel till en ny spelare, fylla i en saknad variant eller skapa nytt kortattribut.
- Discovery Engine 2.0 använder nu Bad Listing Hunter som ytterligare väg till djupanalys, utan att ändra KÖP-krav eller värdering.
- Ny novice-expander **Dåligt beskrivna annonser – kan vara lättare att missa** visar upp till fem kandidater, annonsbrister, varför och vad som bör kontrolleras först.
- Ingen ny fyndscore skapas.
- Ingen KÖP-, värderings-, maxpris-, sold-, risk- eller slutlig rankinglogik ändras.
