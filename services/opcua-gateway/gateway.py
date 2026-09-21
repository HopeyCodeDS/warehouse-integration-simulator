import asyncio
import logging
import json
import uuid
import os
import time
import paho.mqtt.client as mqtt
from asyncua import Client
from asyncua.common.subscription import SubHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OPC-UA-Gateway")

# MQTT Setup
MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

PLC_URL = "opc.tcp://opcua-plc-simulator:4840/freeopcua/server/"
NAMESPACE_URI = "http://examples.freeopcua.github.io"

class MySubHandler(SubHandler):
    """
    First Principle: Event-Driven OT.
    We don't poll the PLC. We subscribe to changes.
    Datachange_notification is SYNCHRONOUS — no await allowed here.
    """
    def datachange_notification(self, node, val, data):
        
        logger.info(f"[Gateway] 🔔 Data Change: {node.nodeid} -> {val}")
        
        if node.nodeid.Identifier.endswith("Sensor_Dock3") and val is True:
            message = {
                "event": "PALLET_ARRIVED",
                "location": "Dock-3",
                "source": "PLC_Conveyor1",
                "correlation_id": str(uuid.uuid4()),
            }
            mqtt_client.publish("warehouse/events/sensor", json.dumps(message))
            logger.info("[Gateway] 📡 Published MQTT event: PALLET_ARRIVED")
        elif str(node.nodeid.Identifier).endswith(("Running", "Speed", "Occupied", "Direction", "PalletId", "Jam")):
            message = {
                "schema_version": "1.0",
                "message_id": str(uuid.uuid4()),
                "source": "opcua-gateway",
                "source_timestamp": time.time(),
                "equipment_id": "Conveyor1",
                "tag": str(node.nodeid.Identifier).split(".")[-1],
                "value": val,
            }
            mqtt_client.publish("warehouse/equipment/state", json.dumps(message), qos=1)

async def main():
    # 1. Connect MQTT
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
    mqtt_client.loop_start()
    
    # 2. First Principle: Distributed Time (Retry Loop)
    client = None
    while True:
        try:
            logger.info(f"Attempting to connect to PLC at {PLC_URL}...")
            client = Client(url=PLC_URL)
            await client.connect()
            logger.info("✅ Connected to PLC.")
            break
        except Exception as e:
            logger.warning(f"⚠️ PLC not ready yet ({type(e).__name__}: {e}). Retrying in 3 seconds...")
            if client is not None:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            await asyncio.sleep(3)

    try:
        # 3. First Principle: Dynamic Discovery
        # Ask the server what index our namespace URI was assigned!
        ns_idx = await client.get_namespace_index(NAMESPACE_URI)
        logger.info(f"🔍 Found Namespace URI '{NAMESPACE_URI}' at dynamic index: {ns_idx}")
        
        # Find the nodes dynamically using the discovered namespace index
        conveyor = await client.nodes.objects.get_child(f"{ns_idx}:Conveyor1")
        tag_names = ["Sensor_Dock3", "Running", "Speed", "Occupied", "Direction", "PalletId", "Jam"]
        tag_nodes = [await conveyor.get_child(f"{ns_idx}:{name}") for name in tag_names]
        
        # 4. Create Subscription
        handler = MySubHandler()
        sub = await client.create_subscription(100, handler) 
        for tag_node in tag_nodes:
            await sub.subscribe_data_change(tag_node)
        
        logger.info("👀 Gateway subscribed to Sensor_Dock3. Waiting for events...")
        
        # Keep alive
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"❌ Fatal error in gateway: {e}")
    finally:
        await client.disconnect()
        mqtt_client.loop_stop()

if __name__ == "__main__":
    asyncio.run(main())