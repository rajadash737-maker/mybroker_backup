# Site Visit Android Integration — Phase 1 Report

Date: 2026-11-16

## Result

**Phase 1 is incomplete.** The apps have configurable development URLs, health API methods, and explicit timeouts, but the required live Android-to-FastAPI connectivity check could not be completed. No emulator/device is available through `adb`, and no backend listener was running on `127.0.0.1:8000`.

## Inspected and implemented

- Backend health routes `GET /health` and `GET /up` in `app/main.py` return `{"status":"ok"}` without depending on a database session. An in-process FastAPI test previously returned HTTP 200 for `/health`.
- Both Android apps now read `BASE_URL` through `BuildConfig`. Debug builds default to the Android emulator host alias `http://10.0.2.2:8000/`; a `BASE_URL` in each local `local.properties` can override it for a physical device. Release configuration retains its separate production base URL; it was not contacted or verified.
- Both apps expose a Retrofit `GET /health` method. Buyer API initialization no longer logs the configured base URL.
- Explicit 30-second connect, read, and write timeouts are configured for Buyer authenticated and token-refresh clients, and Admin authenticated and refresh clients.
- The prior notification timeout used the old debug fallback `10.44.238.22`. That host value is not reliable as an emulator-to-host address, and the request failed while no backend listener was available. For an emulator, the configured `10.0.2.2` alias targets the development host; for a physical device, `local.properties` must contain the host's current LAN-reachable URL.

## Files changed for Phase 1

- Buyer: `app/build.gradle.kts`, `app/src/main/java/com/example/myapplication/core/config/AppEnv.kt`, `app/src/main/java/com/example/myapplication/network/ApiClient.kt`, `app/src/main/java/com/example/myapplication/network/ApiService.kt`.
- Admin: `app/build.gradle.kts`, `app/src/main/java/com/example/mybroker_admin/core/config/AppEnv.kt`, `app/src/main/java/com/example/mybroker_admin/data/remote/ApiClient.kt`, `app/src/main/java/com/example/mybroker_admin/data/remote/api/BackendHealthApi.kt`.

## Verification

- Buyer `:app:compileDebugKotlin`: **BUILD SUCCESSFUL** (1m 22s).
- Admin `:app:compileDebugKotlin`: **BUILD FAILED**. Compilation reports unresolved references across `RootNavGraph.kt` (including existing dashboard, login, listing, refund, notification, and field workflow screens) and dashboard component references. This run does not establish whether those failures predate current work; they need a clean baseline comparison before attribution.
- Buyer `:app:testDebugUnitTest`: **BUILD SUCCESSFUL** (1m 36s).
- Admin `:app:testDebugUnitTest`: **FAILED** during `:app:compileDebugKotlin` with the unresolved-reference errors above; unit tests did not execute.
- Host HTTP check to `http://127.0.0.1:8000/health`: **connection refused**; no server was listening.
- Android emulator/device HTTP check and Logcat: **not run**; `adb` is unavailable.
- No database, MySQL connection, migration, or grant operation was performed.

## Backend contract gaps for later phases

- No Field Officer assigned Site Visit list route (`GET /site-visits/field-officer/my-visits`) exists. The Field Officer start and completion routes exist, but the list endpoint must be supplied before Phase 5 can be completed.
- The Admin detail response does not currently include the seller name/mobile snapshots required by the requested Admin screen.

## Gate

Do not start Phase 2 until a running development backend can be reached from the target Android emulator/device and both Android debug builds compile. Admin build errors need resolution or a known-good baseline; actual Android health response and Logcat evidence are still required.

Code for later Site Visit flows had been drafted in the Android apps before the Phase 1 gate was re-applied. Those phases are not reported as completed or verified; implementation should resume in the required order after this gate is met.
