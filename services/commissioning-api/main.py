import asyncio
import requests
import paho.mqtt.client as mqtt
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from asyncua import Client
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    POSTGRES_USER: str = "wis_user"
    POSTGRES_PASSWORD: str = "wis_password"
    POSTGRES_DB: str = "warehouse_db"
    DB_HOST: str = "postgres"
    ERP_URL: str = "http://erp-api:8000/health"
    WMS_URL: str = "http://wms-api:8001/health"
    MQTT_HOST: str = "mqtt-broker"
    MQTT_PORT: int = 1883
    OPCUA_URL: str = "opc.tcp://opcua-plc-simulator:4840/freeopcua/server/"

settings = Settings()

# Engine built ONCE: pool creation is expensive; pool_pre_ping detects dead connections.
engine = create_engine(
    f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.DB_HOST}:5432/{settings.POSTGRES_DB}",
    pool_pre_ping=True,
)

app = FastAPI(title="WIS Commissioning API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# ---------- Blocking checks: plain sync functions ----------
def _check_db() -> str:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "OK"
    except Exception:
        return "FAIL"

def _check_http(url: str) -> str:
    try:
        return "OK" if requests.get(url, timeout=2).status_code == 200 else "FAIL"
    except Exception:
        return "FAIL"

def _check_mqtt() -> str:
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.connect(settings.MQTT_HOST, settings.MQTT_PORT, 60)
        client.disconnect()
        return "OK"
    except Exception:
        return "FAIL"

async def check_opcua():
    try:
        async with Client(url=settings.OPCUA_URL) as client:
            # Try to browse the root objects to verify connection
            await client.nodes.objects.get_children()
        return "OK"
    except Exception: return "FAIL"

async def _guarded(coro, timeout: float = 5.0) -> str:
    """One hung dependency must never stall the whole report."""
    try:
        return await asyncio.wait_for(coro, timeout)
    except asyncio.TimeoutError:
        return "TIMEOUT"

@app.get("/api/health-check")
async def run_diagnostics():
    # Blocking I/O offloaded to worker threads -> gather is REAL concurrency now.
    db, erp, wms, mqtt_status, opcua = await asyncio.gather(
        _guarded(asyncio.to_thread(_check_db)), 
        _guarded(asyncio.to_thread(_check_http, settings.ERP_URL)), 
        _guarded(asyncio.to_thread(_check_http, settings.WMS_URL)), 
        _guarded(asyncio.to_thread(_check_mqtt)), 
        _guarded(check_opcua)
    )
    
    return {
        "database": db,
        "erp_service": erp,
        "wms_service": wms,
        "mqtt_broker": mqtt_status,
        "opcua_plc": opcua,
        "timestamp": "Live"
    }