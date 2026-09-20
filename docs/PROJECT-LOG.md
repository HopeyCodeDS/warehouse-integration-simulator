# Project Engineering Log

This is the append-only technical record for implementation work in the Warehouse Integration Simulator. Add the newest entry at the top. Keep entries concise but concrete enough to reconstruct why a change exists and how it was verified.

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
