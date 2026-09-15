# Realistic WIS HMI

Enterprise-style dual visualization frontend for the Warehouse Integration Simulator.

- `2D Operations`: dispatching, monitoring, commissioning, and dense operational scanning.
- `3D Twin`: orbitable procedural warehouse scene for inspection, simulation, and stakeholder demos.
- Both views consume the same MQTT state and fall back to reference telemetry when the broker is unavailable.

## Run

```bash
npm install
npm run dev
```

The app runs at `http://localhost:5174` and connects to MQTT over WebSockets at `ws://localhost:9001`.
