import json
import os
import time

import paho.mqtt.client as mqtt

ROBOT_ID = os.getenv("ROBOT_ID", "AMR-Ultra")
FLEET_IDS = [item.strip() for item in os.getenv("FLEET_IDS", "AMR-Ultra,AMR-Nova,AMR-Orbit,AMR-Vega").split(",") if item.strip()]
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))

STATE_IDLE = "IDLE"
STATE_MOVING = "MOVING"
STATE_DOCKED = "DOCKED"

HOME_POSITIONS = {
    "AMR-Ultra": {"x": 420, "y": 340},
    "AMR-Nova": {"x": 500, "y": 205},
    "AMR-Orbit": {"x": 270, "y": 420},
    "AMR-Vega": {"x": 685, "y": 320},
}
ROUTES = {
    "AMR-Ultra": [{"x": 420, "y": 340}, {"x": 420, "y": 205}, {"x": 685, "y": 205}, {"x": 685, "y": 287}],
    "AMR-Nova": [{"x": 500, "y": 205}, {"x": 500, "y": 275}, {"x": 685, "y": 275}],
    "AMR-Orbit": [{"x": 270, "y": 420}, {"x": 420, "y": 420}, {"x": 420, "y": 340}],
    "AMR-Vega": [{"x": 685, "y": 320}, {"x": 685, "y": 370}, {"x": 770, "y": 370}],
}

current_state = STATE_IDLE
current_task = None
current_correlation = None
current_position = HOME_POSITIONS.get(ROBOT_ID, HOME_POSITIONS["AMR-Ultra"]).copy()
battery = 90


def task_belongs_to_robot(payload):
    order_number = payload.get("order_number", "")
    assigned_index = sum(ord(character) for character in order_number) % len(FLEET_IDS)
    return FLEET_IDS[assigned_index] == ROBOT_ID


def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[{ROBOT_ID}] Connected to MQTT Broker with result code {rc}")
    client.subscribe("warehouse/tasks/new")


def on_message(client, userdata, msg):
    global current_state, current_task, current_correlation

    try:
        payload = json.loads(msg.payload.decode())
        if not task_belongs_to_robot(payload):
            return
        if current_state == STATE_IDLE:
            current_task = payload
            current_correlation = payload.get("correlation_id")
            current_state = STATE_MOVING
            publish_state(client, STATE_MOVING, current_task.get("order_number"), current_correlation)
            print(f"[{ROBOT_ID}] Received task for {current_task.get('order_number')}")
    except Exception as error:
        print(f"[{ROBOT_ID}] Error processing message: {error}")


def publish_state(client, state, order_number=None, correlation=None, velocity=0):
    message = {
        "robot_id": ROBOT_ID,
        "state": state,
        "position": current_position,
        "route": ROUTES.get(ROBOT_ID, ROUTES["AMR-Ultra"]),
        "battery": battery,
        "velocity": velocity,
        "task_id": current_task.get("task_id") if current_task else None,
        "order_number": order_number,
        "correlation_id": correlation,
        "timestamp": time.time(),
    }
    client.publish("warehouse/robot/state", json.dumps(message), qos=1, retain=True)


def move_along_route(client):
    global current_position, battery
    route = ROUTES.get(ROBOT_ID, ROUTES["AMR-Ultra"])
    for target in route[1:]:
        start = current_position.copy()
        for step in range(1, 7):
            progress = step / 6
            current_position = {
                "x": round(start["x"] + (target["x"] - start["x"]) * progress),
                "y": round(start["y"] + (target["y"] - start["y"]) * progress),
            }
            battery = max(20, battery - 1)
            publish_state(client, STATE_MOVING, current_task.get("order_number"), current_correlation, velocity=0.8)
            time.sleep(0.5)


def main():
    global current_state, current_task, current_correlation, current_position, battery

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=ROBOT_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
    client.loop_start()
    print(f"[{ROBOT_ID}] Simulator started. Waiting for tasks...")
    publish_state(client, STATE_IDLE, correlation=None)

    try:
        while True:
            if current_state == STATE_MOVING and current_task:
                move_along_route(client)
                current_state = STATE_DOCKED
                publish_state(client, STATE_DOCKED, current_task.get("order_number"), current_correlation)
                time.sleep(2)
                completed_task = current_task
                current_state = STATE_IDLE
                current_task = None
                current_correlation = None
                current_position = HOME_POSITIONS.get(ROBOT_ID, HOME_POSITIONS["AMR-Ultra"]).copy()
                battery = min(100, battery + 8)
                publish_state(client, STATE_IDLE, correlation=None)
                client.publish("warehouse/tasks/completed", json.dumps({
                    "task_id": completed_task.get("task_id"),
                    "order_number": completed_task.get("order_number"),
                    "correlation_id": completed_task.get("correlation_id"),
                    "robot_id": ROBOT_ID,
                }), qos=1)
            time.sleep(0.5)
    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()