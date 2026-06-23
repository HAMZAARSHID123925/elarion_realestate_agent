import sqlite3

conn = sqlite3.connect('d:/ELARION/elarion_realestate_agent/elarion.db')
c = conn.cursor()

c.execute("SELECT title, city, area, price_lakhs, listing_type FROM properties WHERE property_type='apartment'")
rows = c.fetchall()

print(f"Found {len(rows)} apartments in the database:\n")
for r in rows:
    print(f"- {r[0]} ({r[2]}, {r[1]}) | Price: {r[3]} Lakhs [{r[4].upper()}]")
