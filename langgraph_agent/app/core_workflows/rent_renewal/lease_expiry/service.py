"""
Lease Expiry Service — Phase 1, Workflow #4.

Orchestrates one complete scan run:
  1. Load configuration (windows, timezone)
  2. Query active leases from DB
  3. Classify each lease against windows (rule engine)
  4. Write idempotent events for each crossed window
  5. Record scan run for observability

Per-lease error isolation: a failure on one lease does not abort the scan.
The scan continues and records errors in the run summary.
"""
import logging
import uuid
from datetime import date, datetime
from typing import Dict, Any, List, Optional

from app.core_workflows.rent_renewal.lease_expiry.config import (
    load_expiry_windows,
    load_scan_timezone,
)
from app.core_workflows.rent_renewal.lease_expiry.rule_engine import (
    classify_lease,
    InvalidExpiryDateError,
)
from app.core_workflows.rent_renewal.lease_expiry.event_writer import (
    write_expiry_event,
)
from app.core_workflows.rent_renewal.lease_expiry import repository

logger = logging.getLogger(__name__)


def _generate_run_id() -> str:
    """Generate a unique run ID for this scan."""
    return f"scan-{uuid.uuid4().hex[:12]}"


async def run_expiry_scan(
    trigger_type: str = "manual",
    override_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Execute one complete lease expiry scan.

    Args:
        trigger_type: 'manual' or 'scheduled' — recorded for observability.
        override_date: Business date override (useful for testing).
                       If None, uses today in the configured timezone.

    Returns:
        Summary dict with keys:
            run_id, run_date, leases_scanned, events_created,
            duplicates_skipped, errors_count, status, details
    """
    # --- 1. Configuration ---
    windows = load_expiry_windows()
    tz = load_scan_timezone()
    today = override_date or datetime.now(tz).date()
    run_id = _generate_run_id()

    logger.info(
        "Starting lease expiry scan: run_id=%s date=%s windows=%s trigger=%s",
        run_id,
        today,
        windows,
        trigger_type,
    )

    # --- 2. Record scan start ---
    await repository.create_scan_run(
        run_id=run_id,
        trigger_type=trigger_type,
        window_config=windows,
    )

    summary: Dict[str, Any] = {
        "run_id": run_id,
        "run_date": today.isoformat(),
        "leases_scanned": 0,
        "events_created": 0,
        "duplicates_skipped": 0,
        "errors_count": 0,
        "status": "COMPLETED",
        "details": [],
        "error_details": [],
    }

    # --- 3. Query active leases ---
    try:
        leases = await repository.get_active_leases()
    except Exception as e:
        logger.error("Failed to query active leases: %s", e, exc_info=True)
        summary["status"] = "FAILED"
        summary["errors_count"] = 1
        summary["error_details"].append({
            "lease_id": None,
            "error": f"Failed to query leases: {e}",
        })
        await repository.update_scan_run(
            run_id=run_id,
            status="FAILED",
            errors_count=1,
            error_details=summary["error_details"],
        )
        return summary

    summary["leases_scanned"] = len(leases)
    logger.info("Found %d active leases to scan", len(leases))

    # --- 4. Process each lease (error-isolated) ---
    for lease in leases:
        lease_id = lease["lease_id"]
        tenant_id = lease["tenant_id"]
        property_id = lease["property_id"]
        expiry_date = lease["lease_end_date"]

        try:
            # 4a. Classify
            days_remaining, crossed_windows = classify_lease(
                expiry_date=expiry_date,
                today=today,
                windows=windows,
            )

            if not crossed_windows:
                logger.debug(
                    "Lease %s: %d days remaining, no windows crossed",
                    lease_id,
                    days_remaining,
                )
                summary["details"].append({
                    "lease_id": lease_id,
                    "days_remaining": days_remaining,
                    "crossed_windows": [],
                    "events_written": 0,
                    "duplicates": 0,
                })
                continue

            # 4b. Pre-check existing events (optimization, not safety — DB constraint is safety net)
            existing_windows = await repository.get_existing_event_windows(lease_id)

            events_written = 0
            duplicates = 0

            for window in crossed_windows:
                # Application-level dedup check for performance
                if window in existing_windows:
                    duplicates += 1
                    continue

                inserted = await write_expiry_event(
                    lease_id=lease_id,
                    tenant_id=tenant_id,
                    property_id=property_id,
                    expiry_date=expiry_date,
                    days_remaining=days_remaining,
                    window_days=window,
                    event_date=today,
                    run_id=run_id,
                )
                if inserted:
                    events_written += 1
                else:
                    duplicates += 1

            summary["events_created"] += events_written
            summary["duplicates_skipped"] += duplicates
            summary["details"].append({
                "lease_id": lease_id,
                "days_remaining": days_remaining,
                "crossed_windows": crossed_windows,
                "events_written": events_written,
                "duplicates": duplicates,
            })

        except InvalidExpiryDateError as e:
            logger.warning(
                "Lease %s has invalid expiry date: %s — skipping (flagged for review)",
                lease_id,
                e,
            )
            summary["errors_count"] += 1
            summary["error_details"].append({
                "lease_id": lease_id,
                "error": str(e),
            })

        except Exception as e:
            logger.error(
                "Unexpected error processing lease %s: %s",
                lease_id,
                e,
                exc_info=True,
            )
            summary["errors_count"] += 1
            summary["error_details"].append({
                "lease_id": lease_id,
                "error": f"Unexpected: {e}",
            })

    # --- 5. Record scan completion ---
    final_status = "COMPLETED" if summary["errors_count"] == 0 else "COMPLETED"
    # If ALL leases errored, mark FAILED
    if summary["errors_count"] > 0 and summary["events_created"] == 0 and summary["leases_scanned"] > 0:
        final_status = "FAILED"

    summary["status"] = final_status

    await repository.update_scan_run(
        run_id=run_id,
        leases_scanned=summary["leases_scanned"],
        events_created=summary["events_created"],
        duplicates_skipped=summary["duplicates_skipped"],
        errors_count=summary["errors_count"],
        status=final_status,
        error_details=summary["error_details"] if summary["error_details"] else None,
    )

    logger.info(
        "Scan completed: run_id=%s scanned=%d created=%d dupes=%d errors=%d status=%s",
        run_id,
        summary["leases_scanned"],
        summary["events_created"],
        summary["duplicates_skipped"],
        summary["errors_count"],
        final_status,
    )

    return summary
