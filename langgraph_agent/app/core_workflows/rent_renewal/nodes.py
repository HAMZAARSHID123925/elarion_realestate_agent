"""
Rent Renewal Workflow Nodes.
"""
import logging
from app.core_workflows.rent_renewal.state import RentRenewalState

logger = logging.getLogger(__name__)

def lease_check_node(state: RentRenewalState) -> dict:
    """Checks tenant lease details and calculates renewal terms."""
    logger.info("[Rent Renewal] Checking tenant lease status...")
    return {
        "tenant_decision": None,
        "is_complete": False
    }

def renewal_offer_node(state: RentRenewalState) -> dict:
    """Presents the renewal offer to the tenant."""
    logger.info("[Rent Renewal] Presenting lease renewal offer...")
    return {
        "is_complete": True
    }
