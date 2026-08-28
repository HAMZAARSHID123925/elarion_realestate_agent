"""
Properties Resource Router — Phase 4 API Layer & Phase 9 Dashboard Cards.

Provides REST endpoints for property CRUD, dashboard cards with conversation stats,
status toggle, and delete functionality — all persisted directly to PostgreSQL.
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status, Security

from app.api.schemas import (
    PropertyResponse,
    PropertyDetailResponse,
    PropertyDashboardCard,
    PropertyDashboardResponse,
    UnitResponse,
    PropertyCreateRequest,
    PropertyUpdateRequest,
)
from app.api.auth import require_auth, AuthenticatedUser
from database.property_repository import property_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/properties", tags=["Properties"])


@router.get(
    "",
    response_model=List[PropertyResponse],
    summary="Search Properties",
    description="Searches property listings matching optional city, type, and price filters (Requires Auth)."
)
async def list_properties(
    city: Optional[str] = Query(None, description="City name (e.g. Lahore, Islamabad, Karachi)"),
    property_type: Optional[str] = Query(None, description="Property type (house, apartment, plot, commercial)"),
    min_price: Optional[float] = Query(None, description="Minimum price in PKR lakhs"),
    max_price: Optional[float] = Query(None, description="Maximum price in PKR lakhs"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by Active or Inactive"),
    search: Optional[str] = Query(None, description="Search by title, city, or address"),
    limit: int = Query(50, ge=1, le=100, description="Max results to return"),
    user: AuthenticatedUser = Security(require_auth)
) -> List[PropertyResponse]:
    try:
        props = await property_repository.list_properties(
            city=city,
            property_type=property_type,
            min_price=min_price,
            max_price=max_price,
            status=status_filter,
            search=search,
            limit=limit
        )
        return [
            PropertyResponse(
                property_id=p.get("property_id"),
                title=p.get("title"),
                address=p.get("address", ""),
                city=p.get("city"),
                property_type=p.get("property_type"),
                price_lakhs=float(p.get("price_lakhs") or 0.0),
                status=p.get("status", "Active"),
                units_count=int(p.get("units_count") or 0),
                created_at=p.get("created_at")
            )
            for p in props
        ]
    except Exception as e:
        logger.error(f"Error querying properties: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query properties: {str(e)}"
        )


@router.get(
    "/dashboard",
    response_model=PropertyDashboardResponse,
    summary="Get Property Dashboard Cards with Conversation Stats",
    description="Returns property cards with real-time conversation, maintenance, and escalation counts from PostgreSQL."
)
async def get_property_dashboard_cards(
    search: Optional[str] = Query(None, description="Search by title, city, or address"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by Active or Inactive"),
    property_type: Optional[str] = Query(None, description="Filter by property type"),
    city: Optional[str] = Query(None, description="Filter by city"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    user: AuthenticatedUser = Security(require_auth)
) -> PropertyDashboardResponse:
    try:
        cards = await property_repository.get_property_dashboard_cards(
            search=search,
            status=status_filter,
            property_type=property_type,
            city=city,
            limit=limit
        )
        items = [
            PropertyDashboardCard(
                property_id=c["property_id"],
                title=c.get("title"),
                address=c.get("address"),
                city=c.get("city"),
                property_type=c.get("property_type"),
                price_lakhs=float(c.get("price_lakhs") or 0.0),
                status=c.get("status", "Active"),
                units_count=int(c.get("units_count") or 0),
                conversations_count=int(c.get("conversations_count") or 0),
                maintenance_count=int(c.get("maintenance_count") or 0),
                escalations_count=int(c.get("escalations_count") or 0),
                active_automations=c.get("active_automations", []),
                created_at=c.get("created_at")
            )
            for c in cards
        ]
        return PropertyDashboardResponse(total=len(items), items=items)
    except Exception as e:
        logger.error(f"Error fetching property dashboard cards: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch property dashboard: {str(e)}"
        )


@router.get(
    "/cities",
    response_model=List[str],
    summary="Get Distinct Cities",
    description="Returns distinct city values from properties for filter dropdowns."
)
async def get_distinct_cities(
    user: AuthenticatedUser = Security(require_auth)
) -> List[str]:
    try:
        return await property_repository.get_distinct_cities()
    except Exception as e:
        logger.error(f"Error fetching cities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch cities: {str(e)}"
        )


@router.get(
    "/{property_id}",
    response_model=PropertyDetailResponse,
    summary="Get Property by ID",
    description="Retrieves full property details and associated rental units (Requires Auth)."
)
async def get_property(
    property_id: str,
    user: AuthenticatedUser = Security(require_auth)
) -> PropertyDetailResponse:
    try:
        prop = await property_repository.get_property_by_id(property_id)
        if not prop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property with ID '{property_id}' not found."
            )

        units = await property_repository.get_property_units(property_id)
        unit_models = [
            UnitResponse(
                unit_id=u.get("unit_id"),
                property_id=u.get("property_id"),
                unit_number=u.get("unit_number"),
                created_at=u.get("created_at")
            )
            for u in units
        ]

        return PropertyDetailResponse(
            property_id=prop.get("property_id"),
            title=prop.get("title"),
            address=prop.get("address", ""),
            city=prop.get("city"),
            property_type=prop.get("property_type"),
            price_lakhs=float(prop.get("price_lakhs") or 0.0),
            status=prop.get("status", "Active"),
            units_count=int(prop.get("units_count") or 0),
            created_at=prop.get("created_at"),
            units=unit_models
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching property {property_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve property: {str(e)}"
        )


@router.post(
    "",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Property",
    description="Creates a new property record persisted to PostgreSQL."
)
async def create_property(
    payload: PropertyCreateRequest,
    user: AuthenticatedUser = Security(require_auth)
) -> PropertyResponse:
    try:
        property_id = await property_repository.create_property(payload.model_dump(exclude_unset=True))
        prop = await property_repository.get_property_by_id(property_id)
        return PropertyResponse(**prop)
    except Exception as e:
        logger.error(f"Error creating property: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create property: {str(e)}"
        )


@router.patch(
    "/{property_id}",
    response_model=PropertyResponse,
    summary="Update Property",
    description="Updates specific fields of an existing property. Persisted to PostgreSQL."
)
async def update_property(
    property_id: str,
    payload: PropertyUpdateRequest,
    user: AuthenticatedUser = Security(require_auth)
) -> PropertyResponse:
    try:
        updates = payload.model_dump(exclude_unset=True)
        success = await property_repository.update_property(property_id, updates)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
            
        prop = await property_repository.get_property_by_id(property_id)
        return PropertyResponse(**prop)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating property {property_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update property: {str(e)}"
        )


@router.patch(
    "/{property_id}/status",
    response_model=PropertyResponse,
    summary="Toggle Property Status (Active/Inactive)",
    description="Toggles a property between Active and Inactive. Persisted to PostgreSQL."
)
async def toggle_property_status(
    property_id: str,
    payload: dict,
    user: AuthenticatedUser = Security(require_auth)
) -> PropertyResponse:
    try:
        new_status = payload.get("status", "Active")
        result = await property_repository.toggle_property_status(property_id, new_status)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
        return PropertyResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling property status {property_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle property status: {str(e)}"
        )


@router.delete(
    "/{property_id}",
    summary="Delete Property",
    description="Permanently deletes a property from PostgreSQL. Conversation history is preserved."
)
async def delete_property(
    property_id: str,
    user: AuthenticatedUser = Security(require_auth)
) -> Dict[str, Any]:
    try:
        deleted = await property_repository.delete_property(property_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property '{property_id}' not found or could not be deleted."
            )
        return {
            "status": "success",
            "property_id": property_id,
            "message": f"Property '{property_id}' deleted and removed from PostgreSQL database successfully."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting property '{property_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete property: {str(e)}"
        )
