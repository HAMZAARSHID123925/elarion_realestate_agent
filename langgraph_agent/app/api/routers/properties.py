"""
Properties Resource Router — Phase 4 API Layer & Phase 6 Auth.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status, Security

from app.api.schemas import (
    PropertyResponse,
    PropertyDetailResponse,
    UnitResponse,
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
    limit: int = Query(50, ge=1, le=100, description="Max results to return"),
    user: AuthenticatedUser = Security(require_auth)
) -> List[PropertyResponse]:
    try:
        props = await property_repository.list_properties(
            city=city,
            property_type=property_type,
            min_price=min_price,
            max_price=max_price,
            limit=limit
        )
        return [
            PropertyResponse(
                property_id=p.get("property_id"),
                title=p.get("title"),
                address=p.get("address"),
                city=p.get("city"),
                property_type=p.get("property_type"),
                price_lakhs=float(p.get("price_lakhs") or 0.0),
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
            address=prop.get("address"),
            city=prop.get("city"),
            property_type=prop.get("property_type"),
            price_lakhs=float(prop.get("price_lakhs") or 0.0),
            created_at=prop.get("created_at"),
            units=unit_models
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching property {property_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch property: {str(e)}"
        )
