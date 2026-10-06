# Project Engineering Log

This is the append-only technical record for implementation work in the Warehouse Integration Simulator. Add the newest entry at the top. Keep entries concise but concrete enough to reconstruct why a change exists and how it was verified.

## 2026-10-06 - Continuous Integration and Makefile Shell Repair

### Intent

Close WIS-081 by running the existing checks on every push and pull request, and
repair `make`, which could not execute its own recipes on a developer machine
with Git Bash installed.

### Scope and Ownership

Repository infrastructure. No service runtime behavior changes.

### Files and Services Changed

- [CI workflow](../.github/workflows/ci.yml)
- [Pull request template](../.github/pull_request_template.md)
- [Makefile](../Makefile)
- [.gitignore](../.gitignore)

### Behavior and Contracts

Three CI jobs run on pushes to `main` and `develop` and on every pull request:

- **Python services** — byte-compiles all ten service entrypoints, then runs the
  six stack-free unit suites (54 tests).
- **Compose manifest** — seeds `.env` from `.env.example` and runs
  `docker compose config --quiet`.
- **Realistic HMI** — `npm ci`, `npm run lint`, `npm run build`.

Playwright e2e stays out of CI because it needs the running stack; `make e2e`
remains the local gate for that.

The Python job installs `services/wms-api/requirements.txt` and
`services/integration-engine/requirements.txt`. Only `paho-mqtt` is stubbed in
[tests/support.py](../tests/support.py); `test_wms_allocation` imports the real
WMS app and `test_outbox_processing` the real integration worker, so FastAPI,
SQLAlchemy, `pydantic-settings` and `requests` must be installed. Pointing CI at
the service requirements keeps it on the same pins as the containers.

`make` now pins `SHELL` to `cmd.exe` under a `Windows_NT` guard. Every recipe is
written in Windows shell syntax (`copy`, `if not exist`, `rmdir /s /q`, `echo.`),
but GNU Make resolves `SHELL` to `/bin/bash.exe` when Git Bash is on `PATH`, so
those recipes died with `CreateProcess(NULL, echo., ...) failed` — `make help`
was unusable. The `up-infra` target was removed: it was byte-identical to `up`,
and its "without the frontend" description was wrong, as no frontend service
exists in [docker-compose.yml](../docker-compose.yml).

### Validation

```text
make help          # previously failed with CreateProcess ... e=2
make unit          # Ran 54 tests, OK
```

The dependency set was confirmed against a clean virtual environment holding
only the two requirement files above: 54 tests, OK. The first CI run had failed
with `ModuleNotFoundError: No module named 'fastapi'` and `'requests'`, which is
what prompted the install step.

### Known Limitations

- CI does not exercise the stack, so FAT-02 through FAT-04 and the SAT scenarios
  are still manual.
- The Makefile is now explicitly Windows-only on Windows hosts; a POSIX host
  falls through to the default shell and the `copy`/`rmdir` recipes remain
  unportable.
- `[Simulation] Invalid command: ...` still prints after the unit test summary.
  It escapes `silence_stdout` on a teardown path and does not affect exit codes.

### Follow-up Work

- Narrow `make e2e`, which currently discovers all of `tests/` and so re-runs the
  six stack-free suites alongside the stack-dependent order-flow test.
- Add Dependabot for the three npm workspaces and the eight `requirements.txt`
  files.

### Rollback or Recovery Notes

All changes are additive or configuration-only and revert cleanly with
`git revert`. Deleting `.github/workflows/ci.yml` disables CI; reverting the
Makefile `SHELL` block restores the previous (broken) shell selection.

---

## 2026-10-02 - Order Flow Repair, Service Unit Tests, and Schema Drift Discovery

### Intent

Repair the order-creation path, which was failing on every request, and establish per-service unit coverage so defects of this class are caught without a running stack.

### Scope and Ownership

ERP API owns order creation and the outbox write. The integration engine owns outbox polling and completion handling. The robot simulator owns route generation. The tests are repository-level and own none of the runtime behavior.

### Files and Services Changed

- [ERP API](../services/erp-api/app/main.py)
- [Integration engine worker](../services/integration-engine/worker.py)
- [WMS allocation tests](../tests/test_wms_allocation.py)
- [Outbox processing tests](../tests/test_outbox_processing.py)
- [Robot routing tests](../tests/test_robot_routing.py)
- [Shared test doubles](../tests/support.py)
- [Repository commands](../Makefile)

### Behavior and Contracts

- `create_order` referenced `correlation_id` before assigning it. Python scopes the name local to the function, so every `POST /api/orders` raised `UnboundLocalError` and returned 500. The assignment now precedes the `Order` construction, and one identifier reaches both the order row and the outbox event.
- The outbox poller now filters on `event_type == "ORDER_CREATED"`. It previously passed every `PENDING` row to `process_order_created` and worked only because no other producer wrote `PENDING`.
- The completion loop now handles each message independently with a rollback. A malformed payload or an ERP timeout previously raised out of `run_loop`, past the `while True` in `__main__`, and terminated the worker permanently.
- `make unit` runs the service unit tests with no Docker stack. `make validate` now calls it instead of a hardcoded three-file list.
- Unit tests are hermetic: `tests/support.py` stubs `paho.mqtt.client` and seeds dummy credentials, because both service modules build engines and MQTT clients at import time. `FakeSession` interprets real SQLAlchemy criteria against seeded rows, so allocation tests exercise the `quantity >= qty` predicate rather than a canned result.

### Validation

```text
make unit          54 tests, no stack required
make e2e           56 tests including 2 end-to-end, against the live stack
```

A live order completed the full loop and the audit trail carried one correlation ID across every hop:

```text
ORD-E2E-44D234CC5347  COMPLETED
ORDER_CREATED    ERP                -> Integration_Engine   PROCESSED
TASK_DISPATCHED  Integration_Engine -> WMS                  PROCESSED
ORDER_COMPLETED  WMS                -> ERP                  PROCESSED
```

### Known Limitations

- **Schema drift on persisted volumes.** The first `make e2e` run failed with `column orders.correlation_id does not exist`. The `correlation_id` columns are declared in `database/*.sql`, but Postgres only executes `docker-entrypoint-initdb.d` against an empty data directory, so a volume predating that change never received them. All three tables were affected. Recovery required `docker compose down -v`, which destroys simulation data. This repeats the failure recorded as WIS-009 and is the concrete case for Alembic migrations (WIS-079).
- Emoji banners in service `print()` calls raise `UnicodeEncodeError` when stdout is a cp1252 console. Inside Docker this is harmless, but the integration engine's own `except` swallows it and marks the event `ERROR`, so outbox state is corrupted silently. Tests redirect stdout to work around it.
- A failed outbox event is marked `ERROR` and dropped. There is still no retry or backoff.
- No unit tests exist for the ERP service itself; `create_order` is covered only by the end-to-end test.
- FAT-02 through FAT-04 and all SAT scenarios remain unexecuted.

### Follow-up Work

- Replace `init.sql` with Alembic migrations so schema changes reach existing volumes (WIS-079).
- Replace `print()` with the `logging` module across services and drop the emoji banners.
- Add retry and backoff for failed outbox events, distinguishing transient from permanent failures.
- Add GitHub Actions CI running `make unit` (WIS-081).
- Add ERP service unit tests covering `create_order` and the outbox write.

### Rollback or Recovery Notes

The code changes are additive and revert cleanly with `git revert`. The volume reset performed during validation is not reversible; a fresh `make up` reseeds inventory from `database/05_seed_data.sql`.

---

## 2026-09-21 - README Scope and Backlog Clarification

### Intent

Keep the root README focused on the current simulator story while moving broader engineering backlog items into the project log.

### Implemented

- Tightened the README limitations section to the two project-specific simulation gaps that matter most to readers.
- Added an explicit note in the README that broader engineering backlog items are tracked in this project log instead of being listed in the top-level README.

### Backlog

- Retry hardening and service-to-service resilience improvements.
- Richer error handling for cross-service calls and operational failures.
- Broader observability and metrics for the running stack.
- Production-grade deployment practices and environment hardening.

### Remaining Boundary

- These backlog items stay intentionally out of the root README so the top-level narrative stays centered on the simulator, the current demos, and the agentic AI direction.

## 2026-09-20 - Demo Media and Sample Cleanup

### Intent

Improve the top-level README media surface and remove real-brand names from sample dispatch data.

### Implemented

- Added a README demo-media section linking the current HMI screenshot and the 2D/3D demo videos in `assets/`.
- Replaced Toyota-branded sample customer names with a generic fictional customer across the active frontends and Makefile examples.
- Simplified ERP seed product names so the demo data reads as generic sample inventory instead of a real brand catalog.

### Validation

- Reviewed the README media section for consistency with the asset folder.
- Searched active source files to confirm `Toyota` no longer appears in the editable runtime paths.

### Remaining Boundary

- The recorded videos are linked as demo evidence; if they become stale, they should be replaced rather than reworded.

## 2026-09-20 - Frontend Consolidation Documentation

### Intent

Document the plan to keep only the operator dashboard and realistic HMI on `main` while retiring the older twin-style frontends.

### Implemented

- Updated the root README to describe the two retained frontends and remove the old `frontend/digital-twin` quick-start path.
- Updated the WIS Digital Twin evolution note to mark `frontend/digital-twin` and `frontend/wis-digital-Twin-v2` as historical references rather than active main-branch UIs.
- Updated the docs index to list the two active frontends and call out the retired twin-style UIs.

### Validation

- Documentation links were reviewed for consistency against the current repo layout.

### Remaining Boundary

- The actual removal or archiving of the older frontend folders should happen in the same branch cleanup commit so the docs and filesystem stay aligned.

## 2026-09-20 - Simulation Control and Documentation Cleanup

### Intent

Document the lightweight simulation-control service and reduce noisy frontend/runtime artifacts from the repo state.

### Implemented

- Added `services/simulation-control/` as an MQTT-backed control plane for simulation state, tick advancement, pause/resume, step, and speed changes.
- Wired the service into Docker Compose and added tests for command handling, clamping, and step behavior.
- Narrowed the React dashboard MQTT subscription to the operational topics it actually consumes so the Live Integration Monitor no longer logs the full `warehouse/#` namespace.
- Added repository documentation for the simulation-control limitation: it is a control plane, not an authoritative global clock.
- Confirmed the docs index and implementation log are part of the repo documentation surface.

### Validation

- `frontend/react-dashboard` production build passes after the subscription change.
- Simulation control tests cover pause, resume, step, speed clamping, and invalid payload handling.

### Remaining Boundary

- The simulation-control service does not make the system fully deterministic; robots, PLC, and integration workers still advance on their own loops.
- Generated artifacts such as `__pycache__/` and Playwright `test-results/` remain untracked and should stay out of version control.

## 2026-09-16 - Traffic Safety and HMI Regression Foundation

### Intent

Close the remaining safety and regression gaps that can be implemented without inventing an authoritative simulation clock.

### Implemented

- Added `services/traffic-manager/` with undirected route-edge reservations, lease expiry, conflict responses, retries, and release handling.
- Robots now publish reservation requests, enter `WAITING` on conflicts, retry reservations, and release routes after completion.
- Added deterministic traffic tests covering conflicts, release, and opposing robot movement on one aisle.
- Integration Engine now records WMS task dispatch and rejection events in the durable integration ledger.
- Added Playwright configuration and HMI smoke tests for fleet visibility, 2D/3D switching, nonblank WebGL output, and real dispatch feedback.
- Added the Playwright suite to `make validate`.

### Validation

- Traffic and route tests pass: 5 tests.
- Playwright HMI suite passes: 2 tests.
- Realistic HMI lint/build passes.
- Compose configuration and Python compilation pass.
- Traffic manager and robot Docker images build and start.

### Remaining Boundary

- A true simulation clock and replay UI still require an authoritative simulation service; local HMI-only pause controls would be misleading.
- OPC UA TCP connectivity is available, but asyncua service discovery/handshake still requires stabilization before conveyor state can be treated as authoritative.

---

## 2026-09-16 - Documentation System Established

### Intent
Create a durable root documentation entry point for implementation history, technical decisions, validation evidence, and known runtime limitations.

### Documentation Added

- [Documentation index](README.md)
- [Implementation-note template](templates/IMPLEMENTATION-NOTE.md)
- This append-only engineering log

### Working Agreement

Future implementation entries should include:

- Problem or operational goal
- Scope and ownership
- Files and services changed
- Behavior and contracts introduced
- Validation commands and results
- Known limitations, follow-up work, and rollback notes

---

## 2026-09-16 - Realistic IT/OT Simulation Slice

### Intent
Make the warehouse simulation operationally legible across ERP, WMS, MQTT, robot simulators, PLC equipment, and the realistic 2D/3D HMI.

### Scope

- Task-aware robot routing from allocated source rack to destination dock.
- Shared world-coordinate conversion between simulator telemetry and HMI.
- Versioned metadata on WMS task messages and robot completion messages.
- Robot route, waypoint, and progress telemetry.
- HMI order lifecycle projection from MQTT events.
- Conveyor equipment tags and MQTT equipment state.
- 2D and 3D conveyor state visualization.
- Realistic HMI Makefile validation targets.

### Files and Services

- [Simulation route model](../services/robot-simulator/simulation.py)
- [Robot simulator](../services/robot-simulator/worker.py)
- [WMS task publishing](../services/wms-api/app/main.py)
- [OPC UA PLC simulator](../services/opcua-plc-simulator/server.py)
- [OPC UA gateway](../services/opcua-gateway/gateway.py)
- [HMI state adapter](../frontend/realistic-wis-hmi/src/hooks.js)
- [HMI shell and 2D projection](../frontend/realistic-wis-hmi/src/App.jsx)
- [HMI 3D scene](../frontend/realistic-wis-hmi/src/WarehouseScene.jsx)
- [Simulation contract tests](../tests/test_simulation_contract.py)
- [Repository commands](../Makefile)

### Technical Behavior

- WMS allocations now include the source location name, such as `Rack-A2`.
- Robot routes are generated from home position -> source rack -> transfer point -> destination dock.
- Robot telemetry includes world position, legacy-compatible position, route, waypoint index, route progress, message ID, schema version, and timestamps.
- HMI accepts both legacy pixel telemetry and normalized world telemetry.
- Orders move through HMI projections such as `Dispatched`, `In Transit`, `At Dock`, and `Completed`.
- PLC equipment tags include running, speed, occupancy, direction, pallet ID, and jam state.
- 2D conveyor stripes pause when stopped and indicate running/fault state.
- 3D conveyors change color and labels based on equipment state.

### Validation

- `make validate` passes frontend lint/build, Python compilation, simulation contract tests, and Compose validation.
- Docker builds pass for updated WMS, robot, PLC, and gateway services.
- A live in-stock `P200` order completed through ERP -> Integration Engine -> WMS -> robot -> ERP.
- The existing E2E test can fail when repeated local runs exhaust seeded `P100` inventory; this is a fixture-state limitation and is reported by WMS as `409 Insufficient stock`.

### Known Limitations

- The OPC UA gateway currently retries the PLC session handshake; TCP reachability is available, but asyncua service discovery still requires follow-up stabilization.
- Robot traffic reservations, collision avoidance, durable event replay, and simulation clock controls remain future phases.
- Conveyor behavior is now state-aware, but pallet movement and PLC command control are not yet fully modeled.

### Follow-up

- Add versioned Pydantic/JSON Schema contract package.
- Stabilize OPC UA endpoint discovery and add an integration test for tag subscriptions.
- Add deterministic traffic reservations and collision tests.
- Add append-only simulation events and replay projections.
- Add Playwright lifecycle tests for visible robot movement, conveyor state, and order completion.

---

## Entry Format

Use the template in [templates/IMPLEMENTATION-NOTE.md](templates/IMPLEMENTATION-NOTE.md). Newest entries belong above this section.
