# Super Admin Pending Listings Dashboard

## Diagnosis

The dashboard count comes from `GET /admin/sell-land/dashboard/workflow-summary`. The backend response field is `pending_admin_review`; it is a required integer in `AdminDashboardWorkflowSummary`. The Android Retrofit method calls this route, `AdminWorkflowSummaryDto` declares the same `pending_admin_review` JSON key, and `SuperAdminDashboardViewModel` maps that value directly into the pending card state.

The backend endpoint allows both `SUPER_ADMIN` and `ADMIN`. The count follows the existing listing workflow: only requests whose status is `SellLandStatus.PENDING` (`"pending"`) are counted. Draft, approved, field verified, rejected, and later workflow statuses are not counted as pending.

Therefore `N/A` is the Android failure state reached when the workflow-summary request fails. It does not indicate a null or omitted backend count, and the current source does not reveal the runtime cause of an individual failed request (for example, an HTTP/authentication or connectivity failure). A request/response log from the affected session is required to identify that specific failure. A successful response with zero pending listings is mapped to `0`.

## Behavior and coverage

The dashboard refresh reloads the workflow summary. Request failures remain represented by a separate error message, while a successful integer response—including zero—is rendered as a count. Listing verification and role workflows are unchanged.

Backend regression coverage in `tests/test_admin_dashboard_fixes.py` verifies that pending is counted while draft, approved, and rejected listings are excluded, and that an empty listing table returns zero.

## Verification

The focused backend test command could not run in the current environment: neither `pytest` nor a usable `python` executable is available on `PATH`. Android Gradle builds and tests were intentionally not run.
