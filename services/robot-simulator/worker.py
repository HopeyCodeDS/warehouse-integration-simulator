import time
import json
import os
import paho.mqtt.client as mqtt

# --- 1. Configuration (Environment Abstraction) ---
ROBOT_ID = os.getenv("ROBOT_ID", "AMR-01")
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))

# --- 2. State Machine Definitions ---
STATE_IDLE = "IDLE"
STATE_MOVING = "MOVING"
STATE_DOCKED = "DOCKED"

current_state = STATE_IDLE
current_task = None
current_correlation = None

# --- 3. MQTT Callbacks ---
def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[{ROBOT_ID}] Connected to MQTT Broker with result code {rc}")
    # Subscribe to the IT layer's dispatch topic
    client.subscribe("warehouse/tasks/new")

def on_message(client, userdata, msg):
    global current_state, current_task, current_correlation
    
    try:
        payload = json.loads(msg.payload.decode())
        print(f"[{ROBOT_ID}] 📡 Received task: {payload['task_type']} for Order {payload['order_number']}")

        # Extract correlation_id from the incoming task
        correlation_id = payload.get("correlation_id")
        
        # First Principle: State Validation. Only accept tasks if IDLE.
        if current_state == STATE_IDLE:
            current_task = payload
            current_correlation = correlation_id
            current_state = STATE_MOVING
            publish_state(client, STATE_MOVING, current_task['order_number'], current_correlation)
        else:
            print(f"[{ROBOT_ID}] ⚠️ Ignored task. Robot is currently {current_state}")
    except Exception as e:
        print(f"[{ROBOT_ID}] ❌ Error processing message: {e}")

# --- 4. Telemetry Publisher ---
def publish_state(client, state, order_number=None, correlation=None):
    """Publishes the robot's current physical state to the MQTT broker."""
    message = {
        "robot_id": ROBOT_ID,
        "state": state,
        "order_number": order_number,
        "correlation_id": correlation,
        "timestamp": time.time()
    }
    # First Principle: Telemetry. We publish to a dedicated state topic.
    client.publish("warehouse/robot/state", json.dumps(message), qos=1)
    print(f"[{ROBOT_ID}] 📤 Published state: {state}")

# --- 5. The Main Loop (Simulating Physics/Time) ---
def main():
    global current_state, current_task, current_correlation
    
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=ROBOT_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
    client.loop_start() # Starts background network thread
    
    print(f"🤖 {ROBOT_ID} Simulator started. Waiting for tasks...")

    # Announce we are online (no correlation yet since we are idle)
    publish_state(client, STATE_IDLE, correlation=None) 
    
    try:
        while True:
            if current_state == STATE_MOVING:
                print(f"[{ROBOT_ID}] 🚚 Moving to destination... (simulating 3 seconds)")
                time.sleep(3)
                
                current_state = STATE_DOCKED
                publish_state(client, STATE_DOCKED, current_task['order_number'], current_correlation)

                print(f"[{ROBOT_ID}] 📦 Unloading at dock... (simulating 2 seconds)")
                time.sleep(2)
                
                current_state = STATE_IDLE
                current_task = None
                current_correlation = None
                publish_state(client, STATE_IDLE, correlation=None)

                # Physical work done -> publish the receipt the WMS waits for
                client.publish("warehouse/tasks/completed", json.dumps({
                    "task_id": current_task.get("task_id"),
                    "order_number": current_task.get("order_number"),
                    "correlation_id": current_task.get("correlation_id"),
                }), qos=1)
                print(f"[{ROBOT_ID}]  Published task completion receipt")
                
            time.sleep(1) # Main loop sleep
            
    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()