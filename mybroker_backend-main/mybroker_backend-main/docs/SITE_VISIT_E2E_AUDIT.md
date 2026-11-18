# Site Visit E2E Audit

Audit date: 2026-11-15. This is a source-only review; no database connection was made.

## Backend contract

The router is mounted at `/site-visits` by `app/main.py` and defines these routes in `app/site_visits/router.py`:

| Route | Role | Purpose |
|---|---|---|
| `GET /fee` | CUSTOMER | Fee response: rupees, paise, currency |
| `POST /` | CUSTOMER | Create booking from listing, preferred date/time, visitor count, pickup address, optional message and submission key |
| `GET /my-bookings` | CUSTOMER | Owned bookings/status; may return active completion code to owner |
| `POST /{id}/cancel` | CUSTOMER | Buyer cancellation with reason |
| `POST /{id}/payment-order` | CUSTOMER | Create/reuse Razorpay order; response contains booking id, order id, amount in paise, currency, payment status |
| `POST /{id}/verify-payment` | CUSTOMER | Verify order id, payment id and signature server side |
| `POST /{id}/cancel-payment` | CUSTOMER | Mark payment attempt cancelled |
| `GET /admin`, `/admin/summary`, `/admin/field-officers`, `/admin/{id}` | ADMIN or SUPER_ADMIN | Queue, counts, eligible officers, details and assignment history |
| `PUT /admin/{id}/assignment` | ADMIN or SUPER_ADMIN | Assign/reassign an eligible officer, optional note |
| `DELETE /admin/{id}/assignment` | ADMIN or SUPER_ADMIN | Unassign with optional note, subject to service state rules |
| `POST /field-officer/{id}/start` | FIELD_OFFICER | Start assigned visit |
| `POST /field-officer/{id}/completion-code` | FIELD_OFFICER | Initiate completion code; code is delivered through buyer-owned status response |
| `POST /field-officer/{id}/verify-completion` | FIELD_OFFICER | Verify six-digit buyer code |

Auth is bearer JWT through `app/core/dependencies.py`; each route applies role dependencies and the backend service checks active/assigned officer ownership. `app/site_visits/schemas.py` defines the concrete payloads. Booking date cannot be in the past, visitor count is 1–20, address length 10–1000, submission key at most 64 characters. Status values come from `app/site_visits/constants.py`: `pending_payment`, `pending`, `assigned`, `scheduled`, `in_progress`, `completed`, `cancelled`, `refund_pending`, `refunded`, `refund_failed`.

Payment security is handled by `app/site_visits/payment_service.py` plus shared `app/payments/service.py`: the server owns amount calculation, verifies signature/payment state and webhook signatures, and links the order to the visit. Completion code crypto and verification are in `app/site_visits/completion_code.py` and `app/site_visits/service.py`. Notification events are emitted from the service after persistence through `app/notifications/service.py`.

## Client integration status

### Buyer app

No Site Visit-specific API, DTO, repository, screen, ViewModel, or route was present under `app/src/main/java` during audit. Listing details are in `ui/feature/buyer/land_detail/LandDetailScreen.kt` and are navigated from `ui/feature/navigationGraph.kt`; this is the natural booking entry. Existing Retrofit/auth/payment infrastructure is in `network/ApiClient.kt`, `network/ApiService.kt`, and buyer payment modules. Razorpay handling exists in `MainActivity.kt` and `HomeActivity.kt`, but it has not been connected to the backend Site Visit order/verify endpoints. `core/config/AppEnv.kt` currently hardcodes a local base URL, so emulator/device/prod environment separation remains unresolved.

### Admin and Field Officer app

No API or DTO for the `/site-visits/admin*` endpoints was found. The app has Retrofit/auth infrastructure in `data/remote/ApiClient.kt` and API interfaces under `data/remote/api`. `core/navigation/Routes.kt` has `FIELD_SITE_VISIT`, and `feature/fieldofficer/sitevisit/SiteVisitScreen.kt` / `SiteVisitViewModel.kt` implement a different seller listing verification case workflow (photos, location, listing details), not paid buyer Site Visit booking, assignment, start or completion code. No admin booking queue or assignment screen was found. Existing app notification API and Firebase handlers exist, but no Site Visit deep-link routing was found.

## Notifications and database

Backend notification integration exists through `app/notifications/service.py` and the notification router. The client apps have existing FCM services/channels and notification API, but no Site Visit-specific payload routing has been identified. Source confirms revisions `20261115_0037` through `20261115_0042` implement fee, foundation, payment context, payment link, webhook key and completion code. This review did not connect to MySQL and therefore does not independently verify production schema/revision or data. The user-provided migration state is treated as supplied, not revalidated.

## Test evidence and safe test boundary

Backend tests include SQLite in-memory fixtures for buyer, admin/assignment, completion and payment behavior (`tests/test_site_visit_buyer_api.py`, `test_site_visit_admin_api.py`, `test_site_visit_assignment_api.py`, `test_site_visit_completion_code.py`, `test_site_visit_payments.py`). `tests/test_site_visit_payments_mysql.py` is persistent and specifically connects to a MySQL test database; it is excluded from this audit run because runtime configuration must not be allowed to reach `mybroker_db`. No production DB calls, SQL, migrations, or grant changes were made.

## Missing features and implementation plan

1. Add Buyer Retrofit DTO/API/repository/ViewModel/Compose flow for dynamic fee, booking, payment order/checkout/verify, owned status refresh and cancellation; add entry from listing details and a bookings route.
2. Reuse the existing buyer Razorpay activity callback path; only launch checkout from backend order details and call backend verification with callback values. Never log credentials, payment signatures or completion codes.
3. Add Admin Retrofit models/API/repository and queue, summary, detail/history, eligible officer, assignment/reassignment/unassignment screens, with only backend-authorized actions.
4. Add a distinct paid Site Visit Field Officer list/detail workflow in the admin app (do not repurpose seller listing verification); call start, initiate completion, and verify completion endpoints. Provide safe map intent using available listing location data.
5. Route existing notifications to the correct booking screen and request Android 13 notification permission where not already handled.
6. Add focused Android tests and run SQLite-backed backend Site Visit tests. Build both Android apps if the Android project roots are approved for writes/build outputs. Do not run live MySQL E2E without a verified isolated test configuration; never use the production database for tests.
7. Configure dev/emulator/device/prod API origins through non-secret build configuration and preserve existing auth and Retrofit clients.

## Source review scope

Reviewed backend Site Visit router, schemas, constants, service/payment modules, notification integration, app router registration, dependencies, test fixture setup, and Android client source for Retrofit, navigation, listing detail, payment callbacks, field visit workflow and notifications. Existing modified and untracked user files were preserved.
