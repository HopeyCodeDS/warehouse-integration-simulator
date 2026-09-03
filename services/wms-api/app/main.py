from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from .database import SessionLocal, get_db
from .models import Task, Inventory
import paho.mqtt.client as mqtt
import json, os, uuid

app = FastAPI(title="WIS WMS API", version="1.0.0")

# --- MQTT Configuration ---
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))

# Create a global MQTT client
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# --- Pydantic Schemas ---
class ItemLine(BaseModel):
    sku: str
    qty: int

class TaskCreate(BaseModel):
    order_number: str
    task_type: str
    correlation_id: Optional[str] = None
    items: List[ItemLine]
    payload: dict = {}


# ---------- ALLOCATION: reserve stock or reject ----------
def allocate(items: List[ItemLine], db: Session):
    allocations = []
    for line in items:
        inv = (db.query(Inventory)
                 .filter(Inventory.product_sku == line.sku,
                         Inventory.quantity >= line.qty)
                 .first())
        if inv is None:
            raise HTTPException(status_code=409, detail=f"Insufficient stock for {line.sku}")
        allocations.append({"sku": line.sku, "qty": line.qty, "location_id": str(inv.location_id)})
    return allocations

# ---------- CONFIRMATION: robot done -> close digital loop ----------
def on_complete(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == uuid.UUID(data["task_id"])).first()
        if task is None or task.status == "COMPLETED":
            return
        task.status = "COMPLETED"
        # Stock movement: decrement the allocated inventory
        for alloc in (task.payload or {}).get("allocations", []):
            inv = (db.query(Inventory)
                     .filter(Inventory.location_id == uuid.UUID(alloc["location_id"]),
                             Inventory.product_sku == alloc["sku"])
                     .first())
            if inv:
                inv.quantity -= alloc["qty"]
        db.commit()
        print(f"[WMS] ✅ Task COMPLETED. Inventory decremented for {task.order_number}")
        mqtt_client.publish("warehouse/orders/completed", json.dumps({
            "order_number": task.order_number,
            "correlation_id": data.get("correlation_id"),
        }), qos=1)
    except Exception as e:
        db.rollback()
        print(f"[WMS] ❌ Completion handling failed: {e}")
    finally:
        db.close()

# Connect when the app starts
@app.on_event("startup")
def startup():
    """Connect to the MQTT broker."""
    for attempt in range(5):
        try:
            mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
            break
        except Exception:
            import time; time.sleep(2)
    mqtt_client.on_message = on_complete
    mqtt_client.subscribe("warehouse/tasks/completed")
    mqtt_client.loop_start()
    print("[WMS] ✅ Subscribed to warehouse/tasks/completed")

@app.on_event("shutdown")
def shutdown_event():
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    print("[WMS] Disconnected from MQTT Broker")

@app.get("/health")
def health():
    return {"status": "healthy", "service": "wms-api"}

@app.post("/api/tasks", status_code=201)
def receive_task(task_data: TaskCreate, db: Session = Depends(get_db)):
    allocations = allocate(task_data.items, db)  # rejects with 409 if stock short

    # 1. Save to WMS database
    new_task = Task(
        order_number=task_data.order_number,
        task_type=task_data.task_type,
        status="ALLOCATED",
        payload={**task_data.payload,
                 "items": [i.model_dump() for i in task_data.items],
                 "allocations": allocations},
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    print(f"[WMS] Task ALLOCATED from {allocations} for {new_task.order_number}")

    # 2. CROSS THE IT/OT BOUNDARY: Publish to MQTT
    # First Principle: The WMS doesn't know WHO will receive this.
    # It just publishes to a topic. Robots, PLCs, and dashboards subscribe.
    mqtt_topic = "warehouse/tasks/new"
    mqtt_client.publish(mqtt_topic, json.dumps({
        "task_id": str(new_task.id),
        "order_number": new_task.order_number,
        "task_type": new_task.task_type,
        "correlation_id": task_data.correlation_id,
        "payload": new_task.payload,
        "status": "DISPATCHED"
    }), qos=1)

    return {"message": "Task allocated and dispatched", "task_id": str(new_task.id)}