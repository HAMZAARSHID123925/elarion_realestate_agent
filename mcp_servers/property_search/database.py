"""
Database helper — handles SQLite connection and queries.
Production-ready pattern: connection per request, proper error handling.
"""
import sqlite3
import os
from typing import Optional

# Path to SQLite file — goes up to repo root from here
DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "elarion.db"
)

def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory (returns dicts not tuples)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # makes rows behave like dicts
    return conn

def parse_budget(budget_str: str) -> Optional[float]:
    """Convert '200 lakhs' or '1.5 crore' to float in lakhs."""
    if not budget_str:
        return None
    b = budget_str.lower().replace(",", "").strip()
    try:
        if "crore" in b:
            return float(b.replace("crore", "").strip()) * 100
        elif "lakh" in b or "lac" in b:
            return float(b.replace("lakhs", "").replace("lakh", "").replace("lac", "").strip())
        else:
            return float(b)
    except ValueError:
        return None

def search_properties_db(location: str, property_type: str, budget: str) -> list:
    """
    Query SQLite for properties matching filters.
    Uses parameterized queries (prevents SQL injection — production best practice).
    """
    budget_value = parse_budget(budget)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        if budget_value is not None:
            cursor.execute("""
                SELECT * FROM properties
                WHERE LOWER(city) LIKE LOWER(?)
                AND LOWER(property_type) LIKE LOWER(?)
                AND price_lakhs <= ?
                AND is_available = TRUE
                ORDER BY price_lakhs ASC
            """, (f"%{location}%", f"%{property_type}%", budget_value))
        else:
            cursor.execute("""
                SELECT * FROM properties
                WHERE LOWER(city) LIKE LOWER(?)
                AND LOWER(property_type) LIKE LOWER(?)
                AND is_available = TRUE
                ORDER BY price_lakhs ASC
            """, (f"%{location}%", f"%{property_type}%"))

        rows = cursor.fetchall()
        # Convert sqlite3.Row objects to plain dicts
        return [dict(row) for row in rows]
    finally:
        conn.close()   # always close — prevents connection leaks

def get_property_by_id_db(property_id: int) -> Optional[dict]:
    """Get a single property by ID."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM properties WHERE id = ?", (property_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()