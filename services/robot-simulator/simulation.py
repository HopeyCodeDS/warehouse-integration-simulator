from __future__ import annotations

from typing import Any

# Shared world coordinates match frontend/realistic-wis-hmi/src/data.js.
WORLD_WIDTH = 32.0
WORLD_DEPTH = 18.0
LEGACY_WIDTH = 980.0
LEGACY_HEIGHT = 560.0

HOME_POSITIONS = {
    "AMR-Ultra": {"x": 2.5, "z": 3.3},
    "AMR-Nova": {"x": 3.7, "z": -0.2},
    "AMR-Orbit": {"x": -3.5, "z": 7.0},
    "AMR-Vega": {"x": 9.0, "z": 4.2},
}

RACK_POSITIONS = {
    "Rack-A1": {"x": -10.0, "z": -5.5},
    "Rack-A2": {"x": -10.0, "z": -2.8},
    "Rack-B1": {"x": -10.0, "z": 0.2},
    "Rack-B2": {"x": -10.0, "z": 3.2},
    "Rack-C1": {"x": -10.0, "z": 6.2},
    "Rack-D1": {"x": 0.0, "z": -5.5},
    "Rack-D2": {"x": 0.0, "z": -2.8},
    "Rack-E1": {"x": 0.0, "z": 3.2},
    "Rack-E2": {"x": 0.0, "z": 6.2},
}

DOCK_POSITIONS = {
    "Dock-1": {"x": 11.8, "z": -5.2},
    "Dock-2": {"x": 11.8, "z": -1.8},
    "Dock-3": {"x": 11.8, "z": 1.6},
    "Dock-4": {"x": 11.8, "z": 5.0},
}

TRANSFER_POINTS = {
    "Inbound": {"x": 5.6, "z": -5.2},
    "Sort": {"x": 5.6, "z": 0.0},
    "Outbound": {"x": 5.6, "z": 5.2},
}


def world_to_legacy(point: dict[str, float]) -> dict[str, int]:
    return {
        "x": round((point["x"] + WORLD_WIDTH / 2) / WORLD_WIDTH * LEGACY_WIDTH),
        "y": round((point["z"] + WORLD_DEPTH / 2) / WORLD_DEPTH * LEGACY_HEIGHT),
    }


def legacy_to_world(point: dict[str, float]) -> dict[str, float]:
    return {
        "x": round(float(point["x"]) / LEGACY_WIDTH * WORLD_WIDTH - WORLD_WIDTH / 2, 3),
        "z": round(float(point.get("y", point.get("z", 0))) / LEGACY_HEIGHT * WORLD_DEPTH - WORLD_DEPTH / 2, 3),
    }


def _point(point: dict[str, float]) -> dict[str, float]:
    return {"x": round(point["x"], 3), "z": round(point["z"], 3)}


def build_route(home: dict[str, float], source_location: str | None, destination_dock: str | None) -> list[dict[str, float]]:
    source = RACK_POSITIONS.get(source_location or "", TRANSFER_POINTS["Inbound"])
    dock = DOCK_POSITIONS.get(destination_dock or "Dock-3", DOCK_POSITIONS["Dock-3"])
    transfer = TRANSFER_POINTS["Sort"]
    return [
        _point(home),
        {"x": source["x"], "z": home["z"]},
        _point(source),
        {"x": transfer["x"], "z": source["z"]},
        _point(transfer),
        {"x": dock["x"] - 2.0, "z": dock["z"]},
        _point(dock),
    ]


def task_route(task: dict[str, Any], robot_id: str) -> list[dict[str, float]]:
    payload = task.get("payload") or {}
    allocations = payload.get("allocations") or []
    source_location = allocations[0].get("source_location") if allocations else payload.get("source_location")
    destination_dock = payload.get("destination_dock") or task.get("destination_dock") or "Dock-3"
    return build_route(HOME_POSITIONS.get(robot_id, HOME_POSITIONS["AMR-Ultra"]), source_location, destination_dock)
