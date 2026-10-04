# Warehouse Integration Simulator Documentation

This directory contains the durable technical record for the Warehouse Integration Simulator.

## Start Here

- [Project Engineering Log](PROJECT-LOG.md): append-only record of implementation work, decisions, validation, and known blockers.
- [FAT](FAT.md): factory acceptance testing.
- [SAT](SAT.md): site acceptance testing.
- [Architecture Decision Records](adr/): durable decisions and their consequences.

## Active Frontends

- [Operator dashboard](../frontend/react-dashboard): command, monitoring, and live integration logs.
- [Realistic HMI](../frontend/realistic-wis-hmi): warehouse floor visualization and telemetry view.

`frontend/wis-digital-Twin-v2` has been removed. `frontend/digital-twin` is still present but is no longer maintained and is not referenced by any `make` target.

## Documentation Rules

1. Every meaningful implementation task gets one entry in `PROJECT-LOG.md`.
2. Each entry records the date, intent, files changed, technical behavior, validation, and remaining risks.
3. Architectural decisions that affect service boundaries, protocols, data ownership, or state models get a new ADR under `docs/adr/`.
4. Update the project log in the same change as the implementation whenever practical.
5. Prefer links to source files, tests, plans, and commands over copied code.
6. Record known failures honestly, including environment or fixture limitations.

## Entry Template

Copy [templates/IMPLEMENTATION-NOTE.md](templates/IMPLEMENTATION-NOTE.md) into a new log entry or use it as the structure for an update.

## Current Runtime References

- Realistic HMI: `frontend/realistic-wis-hmi`
- ERP API: `http://localhost:8000`
- WMS API: `http://localhost:8001`
- Commissioning API: `http://localhost:8002`
- MQTT WebSocket: `ws://localhost:9001`
- OPC UA PLC: `opc.tcp://localhost:4840/freeopcua/server/`
- Primary validation: `make validate`
- Service unit tests, no stack required: `make unit`
- Full order-flow test, requires the running stack: `make e2e`
