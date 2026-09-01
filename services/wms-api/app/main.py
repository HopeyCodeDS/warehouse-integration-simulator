from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from .models import Task
import paho.mqtt.client as mqtt
import json
import os

app = FastAPI(title="WIS WMS API", version="1.0.0")

# --- MQTT Configuration ---
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))

# Create a global MQTT client
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def connect_mqtt():
    """Connect to the MQTT broker."""
    try:
        mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
        mqtt_client.loop_start()  # Start background thread for network traffic
        print(f"[WMS] ✅ Connected to MQTT Broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    except Exception as e:
        print(f"[WMS] ❌ Failed to connect to MQTT Broker: {e}")

# Connect when the app starts
@app.on_event("startup")
def startup_event():
    connect_mqtt()

@app.on_event("shutdown")
def shutdown_event():
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    print("[WMS] Disconnected from MQTT Broker")

# --- Pydantic Schemas ---
class TaskCreate(BaseModel):
    order_number: str
    task_type: str
    correlation_id: str | None = None
    payload: dict

@app.get("/health")
def health():
    return {"status": "healthy", "service": "wms-api"}

@app.post("/api/tasks", status_code=201)
def receive_task(task_data: TaskCreate, db: Session = Depends(get_db)):
    # 1. Save to WMS database
    new_task = Task(
        order_number=task_data.order_number,
        task_type=task_data.task_type,
        payload=task_data.payload
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    print(f"[WMS] Task saved to database: {new_task.order_number}")

    # 2. CROSS THE IT/OT BOUNDARY: Publish to MQTT
    # First Principle: The WMS doesn't know WHO will receive this.
    # It just publishes to a topic. Robots, PLCs, and dashboards subscribe.
    mqtt_topic = "warehouse/tasks/new"
    mqtt_message = {
        "task_id": str(new_task.id),
        "correlation_id": task_data.correlation_id,
        "order_number": new_task.order_number,
        "task_type": new_task.task_type,
        "payload": new_task.payload,
        "status": "DISPATCHED"
    }

    result = mqtt_client.publish(mqtt_topic, json.dumps(mqtt_message), qos=1)
    
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"[WMS] 📡 Published task to MQTT topic: {mqtt_topic}")
    else:
        print(f"[WMS] ❌ Failed to publish to MQTT. Error code: {result.rc}")

    return {"message": "Task accepted and dispatched to OT layer", "task_id": str(new_task.id)}