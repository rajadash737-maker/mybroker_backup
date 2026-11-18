# Buyer and Seller Offers Badge

## Workflow and count definition

The offer model has no read/unread field. The badge therefore counts actionable incoming offers, not app notifications or unread items:

- `seller_pending`: latest offer for each buyer/listing pair with status `pending` on a listing owned by the authenticated user.
- `buyer_countered`: latest offer for each buyer/listing pair with status `countered` where the authenticated user is the buyer.
- `total`: the sum of those two role-specific counts. This supports users who act as both buyer and seller.

Accepted, rejected, expired and buyer-originated pending offers are excluded. The data model and negotiation rules are unchanged.

## API and app behavior

Added authenticated `GET /sell-land/offers/incoming-count`. It accepts no user ID; the backend derives identity from the access token and restricts the endpoint to `CUSTOMER` accounts. Response fields are `seller_pending`, `buyer_countered`, and `total`. No migration is required.

Android requests the count after Home is shown and whenever Home resumes. Successful offer creation and seller/buyer offer actions also request a refresh. In-flight refreshes are coalesced. A failed request hides the badge and records an error state instead of displaying zero. The badge is hidden for zero, displays counts 1–99, and caps at `99+`.

The Offers entry opens a dedicated hub. Buyer counter-offers open in the existing buyer offers screen filtered to incoming counter-offers; seller offer management opens the existing seller listings and per-listing offer workflow. Existing accept, reject, counter, and buyer booking actions remain in use.

## Changed files

- Backend: `app/sell_land/router.py`, `service.py`, `repository.py`, and `schemas.py`.
- Backend coverage: `tests/test_incoming_offer_counts.py`.
- Android: API DTO/service, Home badge store/top bar, Home lifecycle refresh, Offers hub/navigation, refresh calls after offer actions, and `IncomingOfferBadgeTest.kt`.

## Verification

Backend tests cover buyer and seller counts, sent-offer exclusion, statuses, zero counts, and role authorization. Android unit tests cover badge visibility/formatting and buyer/seller count aggregation. Tests were not run because no Python interpreter or pytest executable is available in the current environment. Android Gradle builds and tests were intentionally not run.

## Remaining verification

Run `pytest tests/test_incoming_offer_counts.py -q` in the backend environment and run `IncomingOfferBadgeTest` from Android Studio. Verify the badge and Offers hub against the supplied Home screenshot and against an authenticated buyer and seller account.
