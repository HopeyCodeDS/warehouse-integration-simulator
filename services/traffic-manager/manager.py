import json
import os
import threading
import time
import uuid


BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
LEASE_SECONDS = 30

reservations = {}
lock = threading.Lock()


def edge_key(start, end):
    points = sorted((f"{start['x']:.3f},{start['z']:.3f}", f"{end['x']:.3f},{end['z']:.3f}"))
    return f"{points[0]}<->{points[1]}"


def requested_edges(route):
    return [edge_key(start, end) for start, end in zip(route, route[1:])]


def purge_expired(now=None):
    now = now or time.time()
    for edge, reservation in list(reservations.items()):
        if reservation["expires_at"] <= now:
            del reservations[edge]


def try_reserve(robot_id, route, request_id):
    now = time.time()
    edges = requested_edges(route)
    with lock:
        purge_expired(now)
        conflicts = [reservations[edge]["robot_id"] for edge in edges if edge in reservations and reservations[edge]["robot_id"] != robot_id]
        if conflicts:
            return False, conflicts[0]
        for edge in edges:
            reservations[edge] = {"robot_id": robot_id, "request_id": request_id, "expires_at": now + LEASE_SECONDS}
        return True, None


def release(robot_id, route):
    with lock:
        for edge in requested_edges(route):
            if edge in reservations and reservations[edge]["robot_id"] == robot_id:
                del reservations[edge]


def on_message(client, userdata, message):
    try:
        payload = json.loads(message.payload.decode())
        if message.topic == "warehouse/traffic/request":
            robot_id = payload["robot_id"]
            request_id = payload.get("request_id", str(uuid.uuid4()))
            granted, conflict = try_reserve(robot_id, payload.get("route", []), request_id)
            client.publish("warehouse/traffic/grant", json.dumps({
                "schema_version": "1.0",
                "message_id": str(uuid.uuid4()),
                "request_id": request_id,
                "robot_id": robot_id,
                "granted": granted,
                "conflict_robot": conflict,
                "expires_at": time.time() + LEASE_SECONDS if granted else None,
            }), qos=1)
        elif message.topic == "warehouse/traffic/release":
            release(payload["robot_id"], payload.get("route", []))
    except (KeyError, TypeError, ValueError) as error:
        print(f"[Traffic] Invalid message: {error}")


def main():
    import paho.mqtt.client as mqtt

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="traffic-manager")
    client.on_message = on_message
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    client.subscribe("warehouse/traffic/request")
    client.subscribe("warehouse/traffic/release")
    client.loop_forever()


if __name__ == "__main__":
    main()
