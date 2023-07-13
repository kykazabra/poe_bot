import json
import requests


league = "Crucible"  # ввод лиги
r = requests.get(f'https://poe.ninja/api/data/currencyoverview?league={league}&type=Currency').json()

items_prices = []

for item in r['lines']:
    if 'receive' in item.keys():
        item_name = item['currencyTypeName']
        value_buy = item['receive']['value']
        value_sell = item['chaosEquivalent']

        items_prices.append({'item_name': item_name, 'price_buy': value_buy, 'price_sell': value_sell})

with open(r'data\items_prices.json', 'w') as f:
    json.dump(items_prices, f, indent=4)