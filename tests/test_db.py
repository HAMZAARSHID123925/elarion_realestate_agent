import sys, os
sys.path.insert(0, os.path.abspath("."))
from mcp_servers.property_search.database import search_properties_db

results = search_properties_db('Lahore', 'house', '300 lakhs')
print(f'Found: {len(results)} properties')
for r in results:
    print(f'  {r["title"]} | {r["price_lakhs"]} lakhs')