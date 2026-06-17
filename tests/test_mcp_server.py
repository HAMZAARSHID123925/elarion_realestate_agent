# """
# Direct test of MCP server tools — no agent needed.
# Run: python tests/test_mcp_server.py
# """
# import sys
# import os
# sys.path.insert(0, os.path.abspath("."))

# from mcp_servers.property_search.server import search_properties, get_property_details

# def test_search_lahore_house():
#     result = search_properties(
#         location="Lahore",
#         property_type="house",
#         budget="200 lakhs"
#     )
#     print("=== Test 1: Lahore House ===")
#     print(f"Status: {result['status']}")
#     print(f"Count: {result['count']}")
#     for p in result['properties']:
#         print(f"  - {p['title']} | {p['price']} lakhs")
#     assert result['status'] == 'success'
#     assert result['count'] >= 1
#     print("✅ PASSED\n")

# def test_search_no_results():
#     result = search_properties(
#         location="Peshawar",
#         property_type="house", 
#         budget="50 lakhs"
#     )
#     print("=== Test 2: No Results ===")
#     print(f"Status: {result['status']}")
#     print(f"Message: {result['message']}")
#     assert result['status'] == 'no_results'
#     print("✅ PASSED\n")

# def test_get_property_details():
#     result = get_property_details(property_id=1)
#     print("=== Test 3: Get Property Details ===")
#     print(f"Status: {result['status']}")
#     print(f"Property: {result['property']['title']}")
#     assert result['status'] == 'success'
#     print("✅ PASSED\n")

# def test_budget_crore():
#     result = search_properties(
#         location="Islamabad",
#         property_type="apartment",
#         budget="1 crore"
#     )
#     print("=== Test 4: Crore Budget ===")
#     print(f"Status: {result['status']}")
#     print(f"Count: {result['count']}")
#     assert result['status'] in ['success', 'no_results']
#     print("✅ PASSED\n")

# if __name__ == "__main__":
#     test_search_lahore_house()
#     test_search_no_results()
#     test_get_property_details()
#     test_budget_crore()
#     print("🎉 All tests passed!")







"""
MCP Server Tests — updated for SQLite backend
Run: python tests/test_mcp_server.py
"""
import sys, os
sys.path.insert(0, os.path.abspath("."))

from mcp_servers.property_search.server import search_properties, get_property_details, get_available_cities

def test_search_lahore_house():
    result = search_properties(location="Lahore", property_type="house", budget="300 lakhs")
    print("=== Test 1: Lahore House ===")
    print(f"Status: {result['status']}")
    print(f"Count: {result['count']}")
    for p in result['properties']:
        print(f"  - {p['title']} | {p['price_lakhs']} lakhs")
    assert result['status'] == 'success'
    assert result['count'] >= 1
    print("PASSED\n")

def test_search_no_results():
    result = search_properties(location="Peshawar", property_type="house", budget="10 lakhs")
    print("=== Test 2: No Results (budget too low) ===")
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    assert result['status'] == 'no_results'
    print("PASSED\n")

def test_get_property_details():
    result = get_property_details(property_id=1)
    print("=== Test 3: Get Property Details ===")
    print(f"Status: {result['status']}")
    print(f"Property: {result['property']['title']}")
    assert result['status'] == 'success'
    print("PASSED\n")

def test_budget_crore():
    result = search_properties(location="Islamabad", property_type="apartment", budget="1 crore")
    print("=== Test 4: Crore Budget ===")
    print(f"Status: {result['status']}")
    print(f"Count: {result['count']}")
    assert result['status'] in ['success', 'no_results']
    print("PASSED\n")

def test_peshawar_properties():
    result = search_properties(location="Peshawar", property_type="house", budget="200 lakhs")
    print("=== Test 5: Peshawar House ===")
    print(f"Status: {result['status']}")
    print(f"Count: {result['count']}")
    for p in result['properties']:
        print(f"  - {p['title']} | {p['price_lakhs']} lakhs")
    assert result['status'] == 'success'
    assert result['count'] >= 1
    print("PASSED\n")

def test_get_cities():
    result = get_available_cities()
    print("=== Test 6: Available Cities ===")
    print(f"Status: {result['status']}")
    for c in result['cities']:
        print(f"  - {c['city']}: {c['total_listings']} listings")
    assert result['status'] == 'success'
    assert len(result['cities']) == 4
    print("PASSED\n")

def test_budget_no_match():
    result = search_properties(location="Islamabad", property_type="house", budget="10 lakhs")
    print("=== Test 7: Budget Too Low ===")
    print(f"Status: {result['status']}")
    assert result['status'] == 'no_results'
    print("PASSED\n")

if __name__ == "__main__":
    test_search_lahore_house()
    test_search_no_results()
    test_get_property_details()
    test_budget_crore()
    test_peshawar_properties()
    test_get_cities()
    test_budget_no_match()
    print("All 7 tests passed!")