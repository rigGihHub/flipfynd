import json
import requests


APP_ID = "5483"
APP_KEY = "BYT_DEN_HÄR_NYCKELN"


def fetch_tradera_data(search_string="hockey", pages=5, items_per_page=50):
    url = "https://api.tradera.com/v3/searchservice.asmx/Search"
    all_results = []

    for page in range(1, pages + 1):
        params = {
            "appId": APP_ID,
            "appKey": APP_KEY,
            "searchString": search_string,
            "pageNumber": page,
            "itemsPerPage": items_per_page
        }

        response = requests.get(url, params=params, timeout=30)
        print(f"Sida {page}: statuskod {response.status_code}")

        if response.status_code != 200:
            print("Fel vid hämtning, avbryter.")
            break

        all_results.append({
            "page": page,
            "raw_response": response.text
        })

    return all_results


if __name__ == "__main__":
    data = fetch_tradera_data(search_string="young guns", pages=3, items_per_page=50)

    with open("next_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Klart. Sparade till next_data.json")