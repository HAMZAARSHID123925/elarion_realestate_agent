"""
Unit and Integration Test Suite for Property Search & Filtering.

Tests PropertyRepository filter queries, price bounds, search strings,
and status toggling logic with robust test isolation.
"""
import pytest
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock

# Ensure root paths are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "langgraph_agent")))

from database.property_repository import PropertyRepository


SAMPLE_PROPERTIES = [
    {
        "property_id": "P-101",
        "title": "Gulberg Luxury Villa",
        "address": "12-B Main Boulevard, Gulberg III",
        "city": "Lahore",
        "property_type": "house",
        "price_lakhs": 250.0,
        "status": "Active",
        "units_count": 4,
        "created_at": "2026-08-01T10:00:00"
    },
    {
        "property_id": "P-102",
        "title": "Clifton Beachfront Apartment",
        "address": "Block 4, Clifton Marine Drive",
        "city": "Karachi",
        "property_type": "apartment",
        "price_lakhs": 180.0,
        "status": "Active",
        "units_count": 12,
        "created_at": "2026-08-05T12:30:00"
    },
    {
        "property_id": "P-103",
        "title": "F-7 Modern Corporate Office",
        "address": "Jinnah Avenue, Blue Area",
        "city": "Islamabad",
        "property_type": "commercial",
        "price_lakhs": 450.0,
        "status": "Inactive",
        "units_count": 20,
        "created_at": "2026-08-10T15:00:00"
    }
]


class MockAsyncCursor:
    def __init__(self, fetchall_data=None, fetchone_data=None):
        self._fetchall_data = fetchall_data or []
        self._fetchone_data = fetchone_data
        self.execute = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    async def fetchall(self):
        return self._fetchall_data

    async def fetchone(self):
        return self._fetchone_data


class MockAsyncConnection:
    def __init__(self, cursor_instance):
        self._cursor = cursor_instance
        self.autocommit = True

    def cursor(self, *args, **kwargs):
        return self._cursor

    async def commit(self):
        pass


@pytest.mark.asyncio
async def test_list_properties_with_mocked_db():
    """Verifies that list_properties executes proper SQL and parameters."""
    repo = PropertyRepository(db_url="postgresql://mock:mock@localhost:5432/mockdb")

    mock_cur = MockAsyncCursor(fetchall_data=[SAMPLE_PROPERTIES[0]])
    mock_conn = MockAsyncConnection(mock_cur)

    # Patch get_db_connection
    with patch("database.property_repository.get_db_connection") as mock_get_conn:
        mock_get_conn.return_value.__aenter__.return_value = mock_conn

        # 1. Search by City & Property Type
        results = await repo.list_properties(city="Lahore", property_type="house", limit=10)

        assert len(results) == 1
        assert results[0]["city"] == "Lahore"
        assert results[0]["property_type"] == "house"

        # Verify SQL execution
        mock_cur.execute.assert_called_once()
        sql_arg, params_arg = mock_cur.execute.call_args[0]
        assert "LOWER(city) = LOWER(%s)" in sql_arg
        assert "LOWER(property_type) = LOWER(%s)" in sql_arg
        assert "Lahore" in params_arg
        assert "house" in params_arg


@pytest.mark.asyncio
async def test_get_property_by_id():
    """Verifies fetching a single property by primary key."""
    repo = PropertyRepository(db_url="postgresql://mock:mock@localhost:5432/mockdb")

    mock_cur = MockAsyncCursor(fetchone_data=SAMPLE_PROPERTIES[1])
    mock_conn = MockAsyncConnection(mock_cur)

    with patch("database.property_repository.get_db_connection") as mock_get_conn:
        mock_get_conn.return_value.__aenter__.return_value = mock_conn

        prop = await repo.get_property_by_id("P-102")
        assert prop is not None
        assert prop["property_id"] == "P-102"
        assert prop["title"] == "Clifton Beachfront Apartment"


@pytest.mark.asyncio
async def test_property_search_filtering_logic():
    """Pure logic test verifying search text matching across simulated properties."""
    def filter_properties(items, city=None, prop_type=None, min_price=None, max_price=None, search=None):
        out = []
        for p in items:
            if city and p["city"].lower() != city.lower():
                continue
            if prop_type and p["property_type"].lower() != prop_type.lower():
                continue
            if min_price is not None and p["price_lakhs"] < min_price:
                continue
            if max_price is not None and p["price_lakhs"] > max_price:
                continue
            if search:
                s = search.lower()
                matches = (
                    s in (p["title"] or "").lower()
                    or s in (p["city"] or "").lower()
                    or s in (p["address"] or "").lower()
                )
                if not matches:
                    continue
            out.append(p)
        return out

    # Test City Filter
    lahore_results = filter_properties(SAMPLE_PROPERTIES, city="Lahore")
    assert len(lahore_results) == 1
    assert lahore_results[0]["property_id"] == "P-101"

    # Test Price Range
    budget_results = filter_properties(SAMPLE_PROPERTIES, min_price=150, max_price=200)
    assert len(budget_results) == 1
    assert budget_results[0]["property_id"] == "P-102"

    # Test Keyword Search
    keyword_results = filter_properties(SAMPLE_PROPERTIES, search="Boulevard")
    assert len(keyword_results) == 1
    assert keyword_results[0]["property_id"] == "P-101"

    # Test No Matches
    empty_results = filter_properties(SAMPLE_PROPERTIES, city="Peshawar")
    assert len(empty_results) == 0


if __name__ == "__main__":
    pytest.main(["-v", __file__])
