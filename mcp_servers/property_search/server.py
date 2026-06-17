# from fastmcp import FastMCP

# # Create the MCP server — this is the "brain plugin"
# mcp = FastMCP("Property Search Server")

# # ─── Fake database (replace with real DB later) ───────────────────────────────
# PROPERTIES = [
#     {
#         "id": 1,
#         "title": "3-Bed House in Gulberg",
#         "city": "Lahore",
#         "type": "house",
#         "price": 150,          # in lakhs PKR
#         "bedrooms": 3,
#         "area_sqft": 1800,
#         "available": True,
#     },
#     {
#         "id": 2,
#         "title": "2-Bed Apartment in F-10",
#         "city": "Islamabad",
#         "type": "apartment",
#         "price": 95,
#         "bedrooms": 2,
#         "area_sqft": 1100,
#         "available": True,
#     },
#     {
#         "id": 3,
#         "title": "Plot in DHA Phase 6",
#         "city": "Karachi",
#         "type": "plot",
#         "price": 200,
#         "bedrooms": 0,
#         "area_sqft": 500,
#         "available": True,
#     },
#     {
#         "id": 4,
#         "title": "5-Bed House in Bahria Town",
#         "city": "Lahore",
#         "type": "house",
#         "price": 350,
#         "bedrooms": 5,
#         "area_sqft": 4000,
#         "available": True,
#     },
#     {
#         "id": 5,
#         "title": "Studio Apartment in Blue Area",
#         "city": "Islamabad",
#         "type": "apartment",
#         "price": 45,
#         "bedrooms": 1,
#         "area_sqft": 600,
#         "available": True,
#     },
# ]

# # ─── Tool 1: Search Properties ────────────────────────────────────────────────
# @mcp.tool()
# def search_properties(
#     location: str,
#     property_type: str,
#     budget: str,
# ) -> dict:
#     """
#     Search for available properties based on user requirements.
    
#     Args:
#         location: The city or area the user wants (e.g. 'Lahore', 'Islamabad')
#         property_type: Type of property (house, apartment, plot)
#         budget: Budget in lakhs PKR as a string (e.g. '100 lakhs', '1.5 crore')
    
#     Returns:
#         A dict with matched properties list and total count.
#     """
    
#     # Parse budget — convert crore to lakhs if needed
#     budget_value = _parse_budget(budget)
    
#     # Filter properties
#     results = []
#     for prop in PROPERTIES:
#         location_match = location.lower() in prop["city"].lower()
#         type_match = property_type.lower() in prop["type"].lower()
#         budget_match = budget_value is None or prop["price"] <= budget_value
        
#         if location_match and type_match and budget_match and prop["available"]:
#             results.append(prop)
    
#     if not results:
#         return {
#             "status": "no_results",
#             "message": f"No {property_type}s found in {location} within your budget.",
#             "properties": [],
#             "count": 0
#         }
    
#     return {
#         "status": "success",
#         "message": f"Found {len(results)} propert(ies) matching your criteria.",
#         "properties": results,
#         "count": len(results)
#     }


# # ─── Tool 2: Get Property Details ─────────────────────────────────────────────
# @mcp.tool()
# def get_property_details(property_id: int) -> dict:
#     """
#     Get full details for a specific property by its ID.
    
#     Args:
#         property_id: The numeric ID of the property
    
#     Returns:
#         Full property details dict, or error if not found.
#     """
#     for prop in PROPERTIES:
#         if prop["id"] == property_id:
#             return {"status": "success", "property": prop}
    
#     return {"status": "error", "message": f"Property with ID {property_id} not found."}


# # ─── Helper: Parse budget string into number ──────────────────────────────────
# def _parse_budget(budget_str: str) -> float | None:
#     """Convert strings like '100 lakhs' or '1 crore' to a float in lakhs."""
#     if not budget_str:
#         return None
    
#     budget_lower = budget_str.lower().replace(",", "")
    
#     try:
#         if "crore" in budget_lower:
#             number = float(budget_lower.replace("crore", "").strip())
#             return number * 100  # 1 crore = 100 lakhs
#         elif "lakh" in budget_lower or "lac" in budget_lower:
#             number = float(budget_lower.replace("lakhs", "").replace("lakh", "").replace("lac", "").strip())
#             return number
#         else:
#             # Assume it's already a plain number in lakhs
#             return float(budget_lower.strip())
#     except ValueError:
#         return None


# # ─── Run the server ───────────────────────────────────────────────────────────
# if __name__ == "__main__":
#     mcp.run(transport="stdio")








"""
Elarion Real Estate MCP Server
Production-grade: SQLite backend, proper error handling, 3 tools.
"""
from fastmcp import FastMCP
from mcp_servers.property_search.database import (
    search_properties_db,
    get_property_by_id_db
)

mcp = FastMCP("Elarion Property Search Server")

# ─── Tool 1: Search Properties ────────────────────────────────────────────────
@mcp.tool()
def search_properties(location: str, property_type: str, budget: str) -> dict:
    """
    Search for available properties matching the user's requirements.

    Args:
        location: City name (Lahore, Islamabad, Karachi, Peshawar)
        property_type: Type of property - house, apartment, plot, commercial
        budget: Budget as string e.g. '200 lakhs', '1.5 crore', '300'

    Returns:
        dict with status, count, and list of matching properties
    """
    try:
        results = search_properties_db(location, property_type, budget)

        if not results:
            return {
                "status": "no_results",
                "message": f"No {property_type}s found in {location} within your budget. Try a higher budget or different area.",
                "properties": [],
                "count": 0
            }

        return {
            "status": "success",
            "message": f"Found {len(results)} {property_type}(s) in {location} within your budget.",
            "properties": results,
            "count": len(results)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Database error: {str(e)}",
            "properties": [],
            "count": 0
        }


# ─── Tool 2: Get Property Details ─────────────────────────────────────────────
@mcp.tool()
def get_property_details(property_id: int) -> dict:
    """
    Get complete details of a specific property by its ID.

    Args:
        property_id: The numeric ID of the property

    Returns:
        Full property details or error if not found
    """
    try:
        prop = get_property_by_id_db(property_id)

        if not prop:
            return {
                "status": "error",
                "message": f"Property with ID {property_id} not found."
            }

        return {"status": "success", "property": prop}

    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}


# ─── Tool 3: Get Available Cities ─────────────────────────────────────────────
@mcp.tool()
def get_available_cities() -> dict:
    """
    Get list of all cities where properties are available.
    Useful when the user hasn't specified a city yet.

    Returns:
        List of available cities with property counts
    """
    import sqlite3, os
    DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "elarion.db")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT city, COUNT(*) as count
            FROM properties
            WHERE is_available = TRUE
            GROUP BY city
            ORDER BY count DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        cities = [{"city": row[0], "total_listings": row[1]} for row in rows]
        return {"status": "success", "cities": cities}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ─── Run the server ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")