"""
Test Suite for Phase 1 — Lease Expiry Tracking (Workflow #4).

Tests:
  - Rule engine: pure date classification logic (unit tests)
  - Config: window loading and validation (unit tests)
  - Integration: service orchestration with mocked repository (integration tests)

Follows existing test_rent_reminder.py conventions.
"""
import pytest
import os
import sys
from datetime import date, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

# Ensure root directories are on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


# ============================================================================
# 1. Rule Engine Unit Tests
# ============================================================================

from app.core_workflows.rent_renewal.lease_expiry.rule_engine import (
    classify_lease,
    compute_days_remaining,
    InvalidExpiryDateError,
)
from app.core_workflows.rent_renewal.lease_expiry.config import EXPIRED_WINDOW_VALUE


class TestComputeDaysRemaining:
    """Tests for the compute_days_remaining helper."""

    def test_future_date(self):
        today = date(2026, 8, 10)
        expiry = date(2026, 9, 10)
        assert compute_days_remaining(expiry, today) == 31

    def test_today_is_expiry(self):
        today = date(2026, 8, 10)
        assert compute_days_remaining(today, today) == 0

    def test_past_date(self):
        today = date(2026, 8, 10)
        expiry = date(2026, 8, 5)
        assert compute_days_remaining(expiry, today) == -5

    def test_exactly_90_days(self):
        today = date(2026, 8, 10)
        expiry = today + timedelta(days=90)
        assert compute_days_remaining(expiry, today) == 90

    def test_exactly_1_day(self):
        today = date(2026, 8, 10)
        expiry = today + timedelta(days=1)
        assert compute_days_remaining(expiry, today) == 1


class TestClassifyLease:
    """Tests for the classify_lease rule engine function."""

    WINDOWS = [90, 60, 30, 7]

    def test_no_windows_crossed(self):
        """Lease 200 days out — should cross no windows."""
        today = date(2026, 1, 1)
        expiry = today + timedelta(days=200)
        days, crossed = classify_lease(expiry, today, self.WINDOWS)
        assert days == 200
        assert crossed == []

    def test_exactly_on_90_day_boundary(self):
        """Lease exactly 90 days away — crosses the 90-day window."""
        today = date(2026, 1, 1)
        expiry = today + timedelta(days=90)
        days, crossed = classify_lease(expiry, today, self.WINDOWS)
        assert days == 90
        assert crossed == [90]

    def test_91_days_no_match(self):
        """Lease 91 days out — should NOT match the 90-day window."""
        today = date(2026, 1, 1)
        expiry = today + timedelta(days=91)
        days, crossed = classify_lease(expiry, today, self.WINDOWS)
        assert days == 91
        assert crossed == []

    def test_89_days_matches_90(self):
        """Lease 89 days out — inside 90-day window."""
        today = date(2026, 1, 1)
        expiry = today + timedelta(days=89)
        days, crossed = classify_lease(expiry, today, self.WINDOWS)
        assert days == 89
        assert 90 in crossed
        assert len(crossed) == 1

    def test_60_day_window(self):
        """Lease 60 days out — crosses both 90 and 60 day windows."""
        today = date(2026, 1, 1)
        expiry = today + timedelta(days=60)
        days, crossed = classify_lease(expiry, today, self.WINDOWS)
        assert days == 60
        assert 90 in crossed
        assert 60 in crossed
        assert 30 not in crossed

    def test_30_day_window(self):
        """Lease 30 days out — crosses 90, 60, and 30 day windows."""
        today = date(2026, 1, 1)
        expiry = today + timedelta(days=30)
        days, crossed = classify_lease(expiry, today, self.WINDOWS)
        assert days == 30
        assert set(crossed) == {90, 60, 30}

    def test_7_day_window(self):
        """Lease 7 days out — crosses all configured windows."""
        today = date(2026, 1, 1)
        expiry = today + timedelta(days=7)
        days, crossed = classify_lease(expiry, today, self.WINDOWS)
        assert days == 7
        assert set(crossed) == {90, 60, 30, 7}

    def test_1_day_remaining(self):
        """Lease 1 day out — crosses all windows."""
        today = date(2026, 1, 1)
        expiry = today + timedelta(days=1)
        days, crossed = classify_lease(expiry, today, self.WINDOWS)
        assert days == 1
        assert set(crossed) == {90, 60, 30, 7}

    def test_expiry_today(self):
        """Lease expires today — crosses all windows plus EXPIRED_WINDOW_VALUE."""
        today = date(2026, 1, 1)
        expiry = today
        days, crossed = classify_lease(expiry, today, self.WINDOWS)
        assert days == 0
        assert EXPIRED_WINDOW_VALUE in crossed
        assert set(crossed) == {90, 60, 30, 7, EXPIRED_WINDOW_VALUE}

    def test_already_expired(self):
        """Lease expired 5 days ago — includes EXPIRED_WINDOW_VALUE."""
        today = date(2026, 1, 10)
        expiry = date(2026, 1, 5)
        days, crossed = classify_lease(expiry, today, self.WINDOWS)
        assert days == -5
        assert EXPIRED_WINDOW_VALUE in crossed

    def test_none_expiry_date(self):
        """None expiry date raises InvalidExpiryDateError."""
        today = date(2026, 1, 1)
        with pytest.raises(InvalidExpiryDateError):
            classify_lease(None, today, self.WINDOWS)

    def test_custom_windows(self):
        """Custom window configuration works."""
        today = date(2026, 1, 1)
        expiry = today + timedelta(days=45)
        custom_windows = [120, 45, 15]
        days, crossed = classify_lease(expiry, today, custom_windows)
        assert days == 45
        assert set(crossed) == {120, 45}

    def test_empty_windows(self):
        """Empty windows list returns empty crossed list."""
        today = date(2026, 1, 1)
        expiry = today + timedelta(days=10)
        days, crossed = classify_lease(expiry, today, [])
        assert days == 10
        assert crossed == []

    def test_empty_windows_expired_lease(self):
        """Empty windows with expired lease still flags EXPIRED_WINDOW_VALUE."""
        today = date(2026, 1, 10)
        expiry = date(2026, 1, 5)
        days, crossed = classify_lease(expiry, today, [])
        assert days == -5
        assert crossed == [EXPIRED_WINDOW_VALUE]


# ============================================================================
# 2. Config Unit Tests
# ============================================================================

from app.core_workflows.rent_renewal.lease_expiry.config import (
    load_expiry_windows,
    load_scan_timezone,
    DEFAULT_EXPIRY_WINDOWS,
)


class TestLoadExpiryWindows:
    """Tests for config window loading."""

    def test_default_windows(self):
        """No env var set — returns defaults."""
        with patch.dict(os.environ, {}, clear=True):
            # Also unset the var explicitly
            os.environ.pop("LEASE_EXPIRY_WINDOWS", None)
            windows = load_expiry_windows()
            assert windows == sorted(DEFAULT_EXPIRY_WINDOWS, reverse=True)

    def test_custom_windows(self):
        """Custom env var parsed correctly."""
        with patch.dict(os.environ, {"LEASE_EXPIRY_WINDOWS": "120,90,45,14"}):
            windows = load_expiry_windows()
            assert windows == [120, 90, 45, 14]

    def test_deduplicated(self):
        """Duplicate values are removed."""
        with patch.dict(os.environ, {"LEASE_EXPIRY_WINDOWS": "30,60,30,90,60"}):
            windows = load_expiry_windows()
            assert windows == [90, 60, 30]

    def test_sorted_descending(self):
        """Windows are sorted descending regardless of input order."""
        with patch.dict(os.environ, {"LEASE_EXPIRY_WINDOWS": "7,90,30,60"}):
            windows = load_expiry_windows()
            assert windows == [90, 60, 30, 7]

    def test_invalid_values_filtered(self):
        """Non-positive values are filtered out."""
        with patch.dict(os.environ, {"LEASE_EXPIRY_WINDOWS": "90,-5,0,30"}):
            windows = load_expiry_windows()
            assert windows == [90, 30]

    def test_invalid_string_falls_back(self):
        """Completely invalid string falls back to defaults."""
        with patch.dict(os.environ, {"LEASE_EXPIRY_WINDOWS": "not,numbers"}):
            windows = load_expiry_windows()
            assert windows == sorted(DEFAULT_EXPIRY_WINDOWS, reverse=True)


class TestLoadScanTimezone:
    """Tests for config timezone loading."""

    def test_default_timezone(self):
        """No env var — returns UTC."""
        os.environ.pop("LEASE_EXPIRY_SCAN_TIMEZONE", None)
        tz = load_scan_timezone()
        assert str(tz) == "UTC"

    def test_custom_timezone(self):
        """Custom timezone parsed correctly."""
        with patch.dict(os.environ, {"LEASE_EXPIRY_SCAN_TIMEZONE": "Asia/Karachi"}):
            tz = load_scan_timezone()
            assert str(tz) == "Asia/Karachi"

    def test_invalid_timezone_falls_back(self):
        """Invalid timezone falls back to UTC."""
        with patch.dict(os.environ, {"LEASE_EXPIRY_SCAN_TIMEZONE": "Not/A/Timezone"}):
            tz = load_scan_timezone()
            assert str(tz) == "UTC"


# ============================================================================
# 3. Event Writer Unit Tests
# ============================================================================

from app.core_workflows.rent_renewal.lease_expiry.event_writer import (
    _build_event_name,
)


class TestBuildEventName:
    """Tests for event name generation."""

    def test_standard_window(self):
        assert _build_event_name(90) == "LEASE_EXPIRY_90_DAYS"
        assert _build_event_name(60) == "LEASE_EXPIRY_60_DAYS"
        assert _build_event_name(30) == "LEASE_EXPIRY_30_DAYS"
        assert _build_event_name(7) == "LEASE_EXPIRY_7_DAYS"

    def test_expired_window(self):
        assert _build_event_name(EXPIRED_WINDOW_VALUE) == "LEASE_EXPIRED"


# ============================================================================
# 4. Service Integration Tests (mocked repository)
# ============================================================================

from app.core_workflows.rent_renewal.lease_expiry.service import run_expiry_scan


class TestRunExpiryScan:
    """Integration tests for the scan service with mocked DB."""

    @pytest.fixture(autouse=True)
    def mock_repository(self):
        """Patch all repository functions for testing."""
        with patch(
            "app.core_workflows.rent_renewal.lease_expiry.service.repository"
        ) as mock_repo:
            mock_repo.create_scan_run = AsyncMock()
            mock_repo.update_scan_run = AsyncMock()
            mock_repo.get_active_leases = AsyncMock(return_value=[])
            mock_repo.get_existing_event_windows = AsyncMock(return_value=set())
            self.mock_repo = mock_repo
            yield mock_repo

    @pytest.fixture(autouse=True)
    def mock_event_writer(self):
        """Patch the event writer."""
        with patch(
            "app.core_workflows.rent_renewal.lease_expiry.service.write_expiry_event",
            new_callable=AsyncMock,
        ) as mock_writer:
            mock_writer.return_value = True  # simulate successful insert
            self.mock_writer = mock_writer
            yield mock_writer

    @pytest.mark.asyncio
    async def test_empty_scan(self):
        """No active leases — scan completes with zero events."""
        self.mock_repo.get_active_leases.return_value = []

        summary = await run_expiry_scan(
            trigger_type="manual",
            override_date=date(2026, 8, 10),
        )

        assert summary["leases_scanned"] == 0
        assert summary["events_created"] == 0
        assert summary["status"] == "COMPLETED"
        self.mock_repo.create_scan_run.assert_called_once()
        self.mock_repo.update_scan_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_lease_outside_all_windows(self):
        """Lease 200 days out — no events created."""
        today = date(2026, 1, 1)
        self.mock_repo.get_active_leases.return_value = [
            {
                "lease_id": "L-001",
                "tenant_id": "T-100",
                "property_id": "P-100",
                "lease_end_date": today + timedelta(days=200),
                "status": "active",
            }
        ]

        summary = await run_expiry_scan(
            trigger_type="manual",
            override_date=today,
        )

        assert summary["leases_scanned"] == 1
        assert summary["events_created"] == 0
        self.mock_writer.assert_not_called()

    @pytest.mark.asyncio
    async def test_lease_in_90_day_window(self):
        """Lease 85 days out — creates 1 event for 90-day window."""
        today = date(2026, 1, 1)
        self.mock_repo.get_active_leases.return_value = [
            {
                "lease_id": "L-001",
                "tenant_id": "T-100",
                "property_id": "P-100",
                "lease_end_date": today + timedelta(days=85),
                "status": "active",
            }
        ]

        summary = await run_expiry_scan(
            trigger_type="manual",
            override_date=today,
        )

        assert summary["leases_scanned"] == 1
        assert summary["events_created"] == 1
        self.mock_writer.assert_called_once()
        # Verify the window_days argument
        call_kwargs = self.mock_writer.call_args
        assert call_kwargs.kwargs.get("window_days") == 90 or call_kwargs[1].get("window_days") == 90

    @pytest.mark.asyncio
    async def test_lease_in_multiple_windows(self):
        """Lease 25 days out — creates events for 90, 60, 30 windows."""
        today = date(2026, 1, 1)
        self.mock_repo.get_active_leases.return_value = [
            {
                "lease_id": "L-001",
                "tenant_id": "T-100",
                "property_id": "P-100",
                "lease_end_date": today + timedelta(days=25),
                "status": "active",
            }
        ]

        summary = await run_expiry_scan(
            trigger_type="manual",
            override_date=today,
        )

        assert summary["leases_scanned"] == 1
        assert summary["events_created"] == 3  # 90, 60, 30
        assert self.mock_writer.call_count == 3

    @pytest.mark.asyncio
    async def test_duplicate_detection_via_existing_events(self):
        """Pre-existing events are skipped via application-level dedup."""
        today = date(2026, 1, 1)
        self.mock_repo.get_active_leases.return_value = [
            {
                "lease_id": "L-001",
                "tenant_id": "T-100",
                "property_id": "P-100",
                "lease_end_date": today + timedelta(days=25),
                "status": "active",
            }
        ]
        # Pretend 90 and 60 already exist
        self.mock_repo.get_existing_event_windows.return_value = {90, 60}

        summary = await run_expiry_scan(
            trigger_type="manual",
            override_date=today,
        )

        assert summary["leases_scanned"] == 1
        assert summary["events_created"] == 1  # only 30
        assert summary["duplicates_skipped"] == 2  # 90 and 60

    @pytest.mark.asyncio
    async def test_expired_lease_generates_expired_event(self):
        """Already-expired lease generates EXPIRED_WINDOW_VALUE event."""
        today = date(2026, 8, 10)
        self.mock_repo.get_active_leases.return_value = [
            {
                "lease_id": "L-005",
                "tenant_id": "T-100",
                "property_id": "P-100",
                "lease_end_date": today - timedelta(days=5),
                "status": "active",
            }
        ]

        summary = await run_expiry_scan(
            trigger_type="manual",
            override_date=today,
        )

        assert summary["leases_scanned"] == 1
        # All 4 windows + expired = 5 events
        assert summary["events_created"] == 5

    @pytest.mark.asyncio
    async def test_per_lease_error_isolation(self):
        """Error on one lease does not abort scan of other leases."""
        today = date(2026, 1, 1)
        self.mock_repo.get_active_leases.return_value = [
            {
                "lease_id": "L-BAD",
                "tenant_id": "T-100",
                "property_id": "P-100",
                "lease_end_date": None,  # invalid!
                "status": "active",
            },
            {
                "lease_id": "L-GOOD",
                "tenant_id": "T-101",
                "property_id": "P-100",
                "lease_end_date": today + timedelta(days=85),
                "status": "active",
            },
        ]

        summary = await run_expiry_scan(
            trigger_type="manual",
            override_date=today,
        )

        assert summary["leases_scanned"] == 2
        assert summary["errors_count"] == 1
        assert summary["events_created"] == 1  # L-GOOD's 90-day event
        assert summary["status"] == "COMPLETED"  # partial success

    @pytest.mark.asyncio
    async def test_multiple_leases(self):
        """Multiple leases in different windows processed correctly."""
        today = date(2026, 1, 1)
        self.mock_repo.get_active_leases.return_value = [
            {
                "lease_id": "L-001",
                "tenant_id": "T-100",
                "property_id": "P-100",
                "lease_end_date": today + timedelta(days=200),  # no match
                "status": "active",
            },
            {
                "lease_id": "L-002",
                "tenant_id": "T-101",
                "property_id": "P-100",
                "lease_end_date": today + timedelta(days=85),  # 90-day window
                "status": "active",
            },
            {
                "lease_id": "L-003",
                "tenant_id": "T-100",
                "property_id": "P-100",
                "lease_end_date": today + timedelta(days=5),  # all windows
                "status": "active",
            },
        ]

        summary = await run_expiry_scan(
            trigger_type="manual",
            override_date=today,
        )

        assert summary["leases_scanned"] == 3
        # L-001: 0, L-002: 1 (90), L-003: 4 (90,60,30,7)
        assert summary["events_created"] == 5

    @pytest.mark.asyncio
    async def test_scan_run_observability(self):
        """Scan run is created at start and updated at completion."""
        self.mock_repo.get_active_leases.return_value = []

        summary = await run_expiry_scan(
            trigger_type="scheduled",
            override_date=date(2026, 8, 10),
        )

        # Verify create_scan_run was called with the right trigger type
        create_call = self.mock_repo.create_scan_run.call_args
        assert create_call.kwargs.get("trigger_type") == "scheduled" or \
               create_call[1].get("trigger_type") == "scheduled"

        # Verify update_scan_run was called with COMPLETED status
        update_call = self.mock_repo.update_scan_run.call_args
        assert update_call.kwargs.get("status") == "COMPLETED" or \
               update_call[1].get("status") == "COMPLETED"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
