"""
Renewal Reminder Template Engine — Phase 2, Workflow #4.

Provides standardized, professional message templates tailored for each
lease expiry window (90, 60, 30, 7 days, and expired).
"""
from typing import Dict, Any, Tuple


def get_template_subject_and_body(
    window_days: int,
    tenant_name: str,
    property_address: str,
    expiry_date_str: str,
    monthly_rent: float = 0.0,
    days_remaining: int = 0,
) -> Tuple[str, str]:
    """
    Renders the subject and body text for a renewal reminder based on the window.

    Returns:
        Tuple of (subject, body_text)
    """
    rent_formatted = f"PKR {monthly_rent:,.2f}" if monthly_rent > 0 else "current rate"

    if window_days >= 90:
        subject = f"Upcoming Lease Expiration Notice (90 Days) — {property_address}"
        body = (
            f"Dear {tenant_name},\n\n"
            f"We hope you are enjoying your stay at {property_address}.\n\n"
            f"This is an advance notice that your current lease is scheduled to expire in "
            f"{days_remaining} days on {expiry_date_str}.\n\n"
            f"We value having you as a resident and would love to discuss renewing your tenancy for another term. "
            f"Your current rent is {rent_formatted}.\n\n"
            f"Please let us know at your convenience if you plan to renew your lease or if you have any questions.\n\n"
            f"Best regards,\n"
            f"Elarion Property Management Team"
        )
    elif window_days >= 60:
        subject = f"Lease Renewal Options Notice (60 Days) — {property_address}"
        body = (
            f"Dear {tenant_name},\n\n"
            f"Your lease agreement for {property_address} will conclude in {days_remaining} days on {expiry_date_str}.\n\n"
            f"To guarantee uninterrupted tenancy and lock in your renewal terms (current rent: {rent_formatted}), "
            f"we kindly request that you review your renewal plans.\n\n"
            f"Please reply to this message indicating whether you wish to renew for another 12-month term or explore other options.\n\n"
            f"Warm regards,\n"
            f"Elarion Property Management Team"
        )
    elif window_days >= 30:
        subject = f"IMPORTANT: Lease Renewal Confirmation Required (30 Days) — {property_address}"
        body = (
            f"Dear {tenant_name},\n\n"
            f"This is an important reminder that your lease at {property_address} expires in "
            f"{days_remaining} days on {expiry_date_str}.\n\n"
            f"As your renewal window is approaching its deadline, please confirm your intention regarding renewal.\n\n"
            f"If you wish to renew, please reply directly so our management team can prepare your updated lease paperwork.\n"
            f"If you plan to vacate, please let us know immediately so we can coordinate move-out procedures.\n\n"
            f"Sincerely,\n"
            f"Elarion Property Management Team"
        )
    elif window_days >= 7:
        subject = f"URGENT: Final Notice — Lease Expiring in {days_remaining} Days — {property_address}"
        body = (
            f"Dear {tenant_name},\n\n"
            f"FINAL NOTICE: Your lease agreement for {property_address} will expire on {expiry_date_str} "
            f"(in {days_remaining} days).\n\n"
            f"We have not yet received confirmation of your renewal intent. Please respond to this notice immediately.\n"
            f"Without a confirmed renewal agreement, the property may be scheduled for inspection and remarketed.\n\n"
            f"Please reply right away to confirm whether you are renewing your tenancy.\n\n"
            f"Urgent regards,\n"
            f"Elarion Property Management Team"
        )
    else:  # Expired (<= 0 days)
        subject = f"URGENT: Lease Agreement Expired — Action Required — {property_address}"
        body = (
            f"Dear {tenant_name},\n\n"
            f"Our records indicate that your lease agreement for {property_address} expired on {expiry_date_str}.\n\n"
            f"You are currently occupying the premises beyond the lease term without an executed renewal agreement.\n"
            f"Please contact management immediately to execute a renewal contract or complete your vacating formalities.\n\n"
            f"Sincerely,\n"
            f"Elarion Property Management Team"
        )

    return subject, body


def render_renewal_reminder_message(
    window_days: int,
    tenant_name: str,
    property_address: str,
    expiry_date_str: str,
    monthly_rent: float = 0.0,
    days_remaining: int = 0,
) -> Dict[str, str]:
    """Convenience wrapper returning a dictionary with subject and body."""
    subject, body = get_template_subject_and_body(
        window_days=window_days,
        tenant_name=tenant_name,
        property_address=property_address,
        expiry_date_str=expiry_date_str,
        monthly_rent=monthly_rent,
        days_remaining=days_remaining,
    )
    return {
        "subject": subject,
        "body": body,
    }
