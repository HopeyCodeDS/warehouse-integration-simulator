import time
import json
import requests
from sqlalchemy import create_engine, Column, String, Integer, DateTime, update, select
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic_settings import BaseSettings
import uuid

# --- 1. Setup Database Connection ---
class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://wis_user:wis_password@postgres:5432/warehouse_db"
    WMS_API_URL: str = "http://wms-api:8001/api/tasks"

settings = Settings()
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 2. Define Models ---
class IntegrationEvent(Base):
    __tablename__ = "integration_events"
    __table_args__ = {'schema': 'integration'}

    id = Column(UUID(as_uuid=True), primary_key=True)
    source = Column(String)
    destination = Column(String)
    event_type = Column(String)
    payload = Column(JSONB)
    status = Column(String)

# --- 3. The Core Logic ---
def process_events():
    db = SessionLocal()
    try:
        # Find unprocessed events
        pending_events = db.query(IntegrationEvent).filter(IntegrationEvent.status == "PENDING").all()
        
        for event in pending_events:
            print(f"[Integration Engine] Found PENDING event: {event.event_type} for Order {event.payload}")
            
            try:
                # A. Transform the payload (ERP language -> WMS language)
                erp_data = event.payload

                # Safety check: If it somehow comes as a string, then I need to parse it.
                if isinstance(erp_data, str):
                    erp_data = json.loads(erp_data)
                
                # The WMS doesn't care about "customers" or "docks" right now.
                # It cares about "Tasks". We translate the ERP order into a WMS Pick Task.
                wms_payload = {
                    "order_number": erp_data["order_number"],
                    "task_type": "PICK_AND_MOVE",
                    "correlation_id": erp_data.get("correlation_id"),
                    "payload": {
                        "customer": erp_data["customer"],
                        "items_count": erp_data["items_count"],
                        "destination": "Dock-3"
                    }
                }

                # B. Route to the WMS API
                print(f"[Integration Engine] Sending translated payload to WMS API...")
                response = requests.post(settings.WMS_API_URL, json=wms_payload, timeout=5)
                
                # C. Handle Response & Update State (Idempotency)
                if response.status_code == 201:
                    event.status = "PROCESSED"
                    print(f"[Integration Engine] ✅ Success! Event marked as PROCESSED.")
                else:
                    event.status = "FAILED"
                    print(f"[Integration Engine] ❌ WMS API rejected the payload.")

            except Exception as e:
                print(f"[Integration Engine] Error processing event {event.id}: {str(e)}")
                event.status = "ERROR"
            
            db.commit()

    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Integration Engine started. Polling for PENDING events...")
    while True:
        process_events()
        time.sleep(2) 