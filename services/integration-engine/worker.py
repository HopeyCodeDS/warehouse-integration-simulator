import time, json, os, uuid, requests
import paho.mqtt.client as mqtt
from queue import Queue
from sqlalchemy import create_engine, Column, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = "warehouse_db"
    DB_HOST: str = "postgres"
    DB_PORT: int = 5432
    WMS_API_URL: str = "http://wms-api:8001/api/tasks"
    ERP_API_URL: str = "http://erp-api:8000/api/orders"
    MQTT_BROKER_HOST: str = "mqtt-broker"
    MQTT_BROKER_PORT: int = 1883

    @property
    def database_url(self):
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.POSTGRES_DB}"

settings = Settings()
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class IntegrationEvent(Base):
    __tablename__ = "integration_events"
    __table_args__ = {'schema': 'integration'}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String)
    destination = Column(String)
    event_type = Column(String)
    correlation_id = Column(String)
    payload = Column(JSONB)
    status = Column(String)


def record_event(db, source, destination, event_type, payload, status="PROCESSED", correlation_id=None):
    db.add(IntegrationEvent(
        source=source,
        destination=destination,
        event_type=event_type,
        correlation_id=correlation_id,
        payload=payload,
        status=status,
    ))

completion_queue = Queue()

def on_mqtt_message(client, userdata, msg):
    completion_queue.put(json.loads(msg.payload.decode()))

def process_order_created(event, db):
    erp_data = event.payload if isinstance(event.payload, dict) else json.loads(event.payload)
    wms_payload = {
        "order_number": erp_data["order_number"],
        "task_type": "PICK_AND_MOVE",
        "correlation_id": erp_data.get("correlation_id"),
        "items": erp_data.get("items", []),
        "payload": {
            "customer": erp_data.get("customer"),
            "destination_dock": erp_data.get("destination_dock"),
        },
    }
    response = requests.post(settings.WMS_API_URL, json=wms_payload, timeout=5)
    if response.status_code == 201:
        event.status = "PROCESSED"
        record_event(db, "Integration_Engine", "WMS", "TASK_DISPATCHED", {
            "order_number": erp_data["order_number"],
            "task_id": response.json().get("task_id"),
            "payload": wms_payload,
        }, correlation_id=erp_data.get("correlation_id"))
        print(f"[Engine] ✅ {erp_data['order_number']} -> WMS (allocated)")
    else:
        event.status = "FAILED"
        record_event(db, "Integration_Engine", "WMS", "TASK_REJECTED", {
            "order_number": erp_data["order_number"],
            "detail": response.text,
        }, status="FAILED", correlation_id=erp_data.get("correlation_id"))
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        print(f"[Engine] ❌ WMS rejected {erp_data['order_number']}: {detail}")

def process_order_completed(data, db):
    # Close the loop: tell the ERP its order is done
    resp = requests.patch(
        f"{settings.ERP_API_URL}/{data['order_number']}/status",
        json={"status": "COMPLETED"}, timeout=5)
    log = IntegrationEvent(source="WMS", destination="ERP", event_type="ORDER_COMPLETED",
                           correlation_id=data.get("correlation_id"),
                           payload=data, status="PROCESSED" if resp.ok else "FAILED")
    db.add(log)
    print(f"[Engine] 📦 {data['order_number']} marked COMPLETED in ERP")

def run_loop():
    db = SessionLocal()
    try:
        for event in db.query(IntegrationEvent).filter(IntegrationEvent.status == "PENDING").all():
            try:
                process_order_created(event, db)
            except Exception as e:
                event.status = "ERROR"
                print(f"[Engine] Error: {e}")
            db.commit()

        while not completion_queue.empty():
            process_order_completed(completion_queue.get(), db)
            db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_mqtt_message
    for _ in range(10):
        try:
            client.connect(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT, 60)
            break
        except Exception:
            time.sleep(2)
    client.subscribe("warehouse/orders/completed")
    client.loop_start()
    print("🚀 Integration Engine started (outbox polling + completion listener)...")
    while True:
        run_loop()
        time.sleep(2)