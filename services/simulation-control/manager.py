import json
import os
import threading
import time
import uuid

BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
TICK_SECONDS = 0.5

state = {
    "schema_version": "1.0",
    "message_id": "",
    "source": "simulation-control",
    "run_id": os.getenv("SIMULATION_RUN_ID", "local-run"),
    "status": "RUNNING",
    "speed": 1.0,
    "tick": 0,
    "scenario": "default",
    "updated_at": 0.0,
}
lock = threading.Lock()


def snapshot():
    with lock:
        return {**state, "message_id": str(uuid.uuid4()), "updated_at": time.time()}


def publish_state(client):
    client.publish("warehouse/simulation/state", json.dumps(snapshot()), qos=1, retain=True)


def handle_command(client, userdata, message):
    try:
        command = json.loads(message.payload.decode())
        name = command.get("command")
        with lock:
            if name == "pause":
                state["status"] = "PAUSED"
            elif name == "resume":
                state["status"] = "RUNNING"
            elif name == "reset":
                state["status"] = "RUNNING"
                state["tick"] = 0
                state["scenario"] = command.get("scenario", "default")
            elif name == "speed":
                state["speed"] = max(0.1, min(float(command.get("value", 1.0)), 8.0))
            elif name == "step":
                state["status"] = "PAUSED"
                state["tick"] += 1
            else:
                return
        publish_state(client)
        if name == "step":
            client.publish("warehouse/simulation/tick", json.dumps(snapshot()), qos=1)
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        print(f"[Simulation] Invalid command: {error}")


def main():
    import paho.mqtt.client as mqtt

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="simulation-control")
    client.on_message = handle_command
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    client.subscribe("warehouse/simulation/command")
    client.loop_start()
    publish_state(client)
    print("[Simulation] Control service started")
    try:
        while True:
            with lock:
                running = state["status"] == "RUNNING"
                speed = state["speed"]
                if running:
                    state["tick"] += 1
            if running:
                payload = snapshot()
                client.publish("warehouse/simulation/tick", json.dumps(payload), qos=1)
                client.publish("warehouse/simulation/state", json.dumps(payload), qos=1, retain=True)
            time.sleep(TICK_SECONDS / speed)
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
