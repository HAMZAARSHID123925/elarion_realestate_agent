"""
Job Registry — Phase 5 Scheduling.

Central catalog of all registered platform background jobs and their target functions.
"""
from typing import Dict, Any, Callable

from app.core_workflows.rent_reminder.scheduler import run_daily_rent_reminder_workflow
from app.core_workflows.rent_renewal.lease_expiry.scheduler_entry import run_lease_expiry_scan
from app.core_workflows.rent_renewal.renewal_reminder.service import run_renewal_reminder_dispatch
from app.jobs.maintenance_monitor import check_stale_maintenance_tickets
from app.jobs.runner import job_runner


JOB_REGISTRY: Dict[str, Dict[str, Any]] = {
    "rent_reminder_scan": {
        "job_name": "rent_reminder_scan",
        "description": "Daily automated scan evaluating overdue rent records and dispatching Day 30/35 reminders.",
        "domain": "Rent Reminder",
        "default_cadence": "Daily @ 08:00 AM",
        "handler": run_daily_rent_reminder_workflow,
        "max_retries": 2
    },
    "lease_expiry_scan": {
        "job_name": "lease_expiry_scan",
        "description": "Daily proactive scan detecting active leases approaching 90, 60, 30, and 7-day expiry windows.",
        "domain": "Rent Renewal",
        "default_cadence": "Daily @ 07:00 AM",
        "handler": run_lease_expiry_scan,
        "max_retries": 2
    },
    "renewal_reminder_scan": {
        "job_name": "renewal_reminder_scan",
        "description": "Daily renewal reminder stage dispatch scan notifying tenants of approaching lease milestones.",
        "domain": "Rent Renewal",
        "default_cadence": "Daily @ 08:30 AM",
        "handler": run_renewal_reminder_dispatch,
        "max_retries": 2
    },
    "maintenance_sla_monitor": {
        "job_name": "maintenance_sla_monitor",
        "description": "Hourly monitor checking for unassigned emergency (>1h) and standard (>24h) maintenance tickets.",
        "domain": "Maintenance",
        "default_cadence": "Hourly",
        "handler": check_stale_maintenance_tickets,
        "max_retries": 2
    }
}


async def run_registered_job(job_name: str, **kwargs) -> Dict[str, Any]:
    """
    Executes a registered job through the resilient JobRunner.
    """
    job_info = JOB_REGISTRY.get(job_name)
    if not job_info:
        raise ValueError(f"Job '{job_name}' is not a registered background job.")

    return await job_runner.execute_job(
        job_name=job_name,
        job_fn=job_info["handler"],
        max_retries=job_info.get("max_retries", 2),
        **kwargs
    )
