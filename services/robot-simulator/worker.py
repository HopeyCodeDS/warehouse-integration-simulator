import json
import os
import time
import uuid
import json
import threading

import paho.mqtt.client as mqtt
from simulation import HOME_POSITIONS, build_route, task_route, world_to_legacy

ROBOT_ID = os.getenv("ROBOT_ID", "AMR-Ultra")
FLEET_IDS = [item.strip() for item in os.getenv("FLEET_IDS", "AMR-Ultra,AMR-Nova,AMR-Orbit,AMR-Vega").split(",") if item.strip()]
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))

STATE_IDLE = "IDLE"
STATE_WAITING = "WAITING"
STATE_MOVING = "MOVING"
STATE_DOCKED = "DOCKED"

current_state = STATE_IDLE
current_task = None
current_correlation = None
current_position = HOME_POSITIONS.get(ROBOT_ID, HOME_POSITIONS["AMR-Ultra"]).copy()
current_route = [current_position]
current_waypoint = 0
reservation_granted = False
last_reservation_request = 0.0
battery = 90
simulation_tick = threading.Event()
simulation_status = "RUNNING"


def task_belongs_to_robot(payload):
    order_number = payload.get("order_number", "")
    assigned_index = sum(ord(character) for character in order_number) % len(FLEET_IDS)
    return FLEET_IDS[assigned_index] == ROBOT_ID


def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[{ROBOT_ID}] Connected to MQTT Broker with result code {rc}")
    client.subscribe("warehouse/tasks/new")
    client.subscribe("warehouse/traffic/grant")
    client.subscribe("warehouse/simulation/state")
    client.subscribe("warehouse/simulation/tick")


def on_message(client, userdata, msg):
    global current_state, current_task, current_correlation, current_route, current_waypoint, reservation_granted, last_reservation_request, simulation_status

    try:
        payload = json.loads(msg.payload.decode())
        if msg.topic == "warehouse/simulation/state":
            simulation_status = payload.get("status", "RUNNING")
            return
        if msg.topic == "warehouse/simulation/tick":
            simulation_tick.set()
            return
        if msg.topic == "warehouse/traffic/grant":
            if current_task and payload.get("robot_id") == ROBOT_ID and payload.get("request_id") == current_task.get("reservation_request_id"):
                reservation_granted = bool(payload.get("granted"))
                current_state = STATE_MOVING if reservation_granted else STATE_WAITING
                publish_state(client, current_state, current_task.get("order_number"), current_correlation)
            return
        if not task_belongs_to_robot(payload):
            return
        if current_state == STATE_IDLE:
            current_task = payload
            current_correlation = payload.get("correlation_id")
            current_route = task_route(payload, ROBOT_ID)
            current_waypoint = 0
            reservation_granted = False
            current_task["reservation_request_id"] = f"{ROBOT_ID}-{time.time_ns()}"
            last_reservation_request = time.time()
            current_state = STATE_WAITING
            client.publish("warehouse/traffic/request", json.dumps({
                "schema_version": "1.0",
                "message_id": str(uuid.uuid4()),
                "request_id": current_task["reservation_request_id"],
                "robot_id": ROBOT_ID,
                "route": current_route,
            }), qos=1)
            publish_state(client, STATE_WAITING, current_task.get("order_number"), current_correlation)
            print(f"[{ROBOT_ID}] Received task for {current_task.get('order_number')}")
    except Exception as error:
        print(f"[{ROBOT_ID}] Error processing message: {error}")


def publish_state(client, state, order_number=None, correlation=None, velocity=0):
    legacy_position = world_to_legacy(current_position)
    message = {
        "schema_version": "1.0",
        "message_id": f"{ROBOT_ID}-{time.time_ns()}",
        "robot_id": ROBOT_ID,
        "state": state,
        "position": {**legacy_position, "z": current_position["z"]},
        "world_position": current_position,
        "route": current_route,
        "legacy_route": [world_to_legacy(point) for point in current_route],
        "waypoint_index": current_waypoint,
        "route_progress": round(current_waypoint / max(len(current_route) - 1, 1), 3),
        "battery": battery,
        "velocity": velocity,
        "task_id": current_task.get("task_id") if current_task else None,
        "order_number": order_number,
        "correlation_id": correlation,
        "timestamp": time.time(),
    }
    client.publish("warehouse/robot/state", json.dumps(message), qos=1, retain=True)


def move_along_route(client):
    global current_position, battery, current_waypoint
    for target_index, target in enumerate(current_route[1:], start=1):
        start = current_position.copy()
        for step in range(1, 7):
            progress = step / 6
            simulation_tick.wait()
            simulation_tick.clear()
            current_position = {
                "x": round(start["x"] + (target["x"] - start["x"]) * progress, 3),
                "z": round(start["z"] + (target["z"] - start["z"]) * progress, 3),
            }
            current_waypoint = target_index
            battery = max(20, battery - 1)
            publish_state(client, STATE_MOVING, current_task.get("order_number"), current_correlation, velocity=0.8)
            time.sleep(0.5)


def main():
    global current_state, current_task, current_correlation, current_position, current_route, current_waypoint, reservation_granted, last_reservation_request, battery

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=ROBOT_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
    client.loop_start()
    print(f"[{ROBOT_ID}] Simulator started. Waiting for tasks...")
    publish_state(client, STATE_IDLE, correlation=None)

    try:
        while True:
            if current_state == STATE_WAITING and current_task and not reservation_granted and time.time() - last_reservation_request >= 3:
                current_task["reservation_request_id"] = f"{ROBOT_ID}-{time.time_ns()}"
                last_reservation_request = time.time()
                client.publish("warehouse/traffic/request", json.dumps({
                    "schema_version": "1.0",
                    "message_id": str(uuid.uuid4()),
                    "request_id": current_task["reservation_request_id"],
                    "robot_id": ROBOT_ID,
                    "route": current_route,
                }), qos=1)
            if current_state == STATE_MOVING and current_task and reservation_granted:
                move_along_route(client)
                current_state = STATE_DOCKED
                publish_state(client, STATE_DOCKED, current_task.get("order_number"), current_correlation)
                time.sleep(2)
                completed_task = current_task
                current_state = STATE_IDLE
                current_task = None
                current_correlation = None
                reservation_granted = False
                current_position = HOME_POSITIONS.get(ROBOT_ID, HOME_POSITIONS["AMR-Ultra"]).copy()
                current_route = [current_position]
                current_waypoint = 0
                battery = min(100, battery + 8)
                publish_state(client, STATE_IDLE, correlation=None)
                client.publish("warehouse/tasks/completed", json.dumps({
                    "schema_version": "1.0",
                    "message_id": f"{ROBOT_ID}-{time.time_ns()}",
                    "source": "robot-simulator",
                    "source_timestamp": time.time(),
                    "task_id": completed_task.get("task_id"),
                    "order_number": completed_task.get("order_number"),
                    "correlation_id": completed_task.get("correlation_id"),
                    "robot_id": ROBOT_ID,
                }), qos=1)
                client.publish("warehouse/traffic/release", json.dumps({
                    "robot_id": ROBOT_ID,
                    "route": current_route,
                }), qos=1)
            time.sleep(0.5)
    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()