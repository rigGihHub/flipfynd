import json

with open("next_data.json", "r", encoding="utf-8") as file:
    data = json.load(file)

discover = data["props"]["pageProps"]["initialState"]["discover"]

print("Nycklar i discover:")
print(list(discover.keys()))
print()

items = discover["items"]

print("Typ av items:", type(items))
print("Antal items:", len(items))
print()

if len(items) > 0:
    print("Första item:")
    print(items[0])
else:
    print("Inga items hittades")