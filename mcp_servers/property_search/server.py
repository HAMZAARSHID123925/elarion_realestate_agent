from fastmcp import FastMCP

# Create the MCP server — this is the "brain plugin"
mcp = FastMCP("Property Search Server")

# ─── Fake database (replace with real DB later) ───────────────────────────────
PROPERTIES = [
    {
        "id": 1,
        "title": "3-Bed House in Gulberg",
        "city": "Lahore",
        "type": "house",
        "price": 150,          # in lakhs PKR
        "bedrooms": 3,
        "area_sqft": 1800,
        "available": True,
    },
    {
        "id": 2,
        "title": "2-Bed Apartment in F-10",
        "city": "Islamabad",
        "type": "apartment",
        "price": 95,
        "bedrooms": 2,
        "area_sqft": 1100,
        "available": True,
    },
    {
        "id": 3,
        "title": "Plot in DHA Phase 6",
        "city": "Karachi",
        "type": "plot",
        "price": 200,
        "bedrooms": 0,
        "area_sqft": 500,
        "available": True,
    },
    {
        "id": 4,
        "title": "5-Bed House in Bahria Town",
        "city": "Lahore",
        "type": "house",
        "price": 350,
        "bedrooms": 5,
        "area_sqft": 4000,
        "available": True,
    },
    {
        "id": 5,
        "title": "Studio Apartment in Blue Area",
        "city": "Islamabad",
        "type": "apartment",
        "price": 45,
        "bedrooms": 1,
        "area_sqft": 600,
        "available": True,
    },
]

# ─── Tool 1: Search Properties ────────────────────────────────────────────────
@mcp.tool()
def search_properties(
    location: str,
    property_type: str,
    budget: str,
) -> dict:
    """
    Search for available properties based on user requirements.
    
    Args:
        location: The city or area the user wants (e.g. 'Lahore', 'Islamabad')
        property_type: Type of property (house, apartment, plot)
        budget: Budget in lakhs PKR as a string (e.g. '100 lakhs', '1.5 crore')
    
    Returns:
        A dict with matched properties list and total count.
    """
    
    # Parse budget — convert crore to lakhs if needed
    budget_value = _parse_budget(budget)
    
    # Filter properties
    results = []
    for prop in PROPERTIES:
        location_match = location.lower() in prop["city"].lower()
        type_match = property_type.lower() in prop["type"].lower()
        budget_match = budget_value is None or prop["price"] <= budget_value
        
        if location_match and type_match and budget_match and prop["available"]:
            results.append(prop)
    
    if not results:
        return {
            "status": "no_results",
            "message": f"No {property_type}s found in {location} within your budget.",
            "properties": [],
            "count": 0
        }
    
    return {
        "status": "success",
        "message": f"Found {len(results)} propert(ies) matching your criteria.",
        "properties": results,
        "count": len(results)
    }


# ─── Tool 2: Get Property Details ─────────────────────────────────────────────
@mcp.tool()
def get_property_details(property_id: int) -> dict:
    """
    Get full details for a specific property by its ID.
    
    Args:
        property_id: The numeric ID of the property
    
    Returns:
        Full property details dict, or error if not found.
    """
    for prop in PROPERTIES:
        if prop["id"] == property_id:
            return {"status": "success", "property": prop}
    
    return {"status": "error", "message": f"Property with ID {property_id} not found."}


# ─── Helper: Parse budget string into number ──────────────────────────────────
def _parse_budget(budget_str: str) -> float | None:
    """Convert strings like '100 lakhs' or '1 crore' to a float in lakhs."""
    if not budget_str:
        return None
    
    budget_lower = budget_str.lower().replace(",", "")
    
    try:
        if "crore" in budget_lower:
            number = float(budget_lower.replace("crore", "").strip())
            return number * 100  # 1 crore = 100 lakhs
        elif "lakh" in budget_lower or "lac" in budget_lower:
            number = float(budget_lower.replace("lakhs", "").replace("lakh", "").replace("lac", "").strip())
            return number
        else:
            # Assume it's already a plain number in lakhs
            return float(budget_lower.strip())
    except ValueError:
        return None


# ─── Run the server ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")