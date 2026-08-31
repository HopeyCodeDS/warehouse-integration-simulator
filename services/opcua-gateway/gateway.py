import asyncio
import logging
import json
import os
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
        
        # We only subscribed to Sensor_Dock3, so any True value is the sensor tripping
        if val is True:
            message = {
                "event": "PALLET_ARRIVED",
                "location": "Dock-3",
                "source": "PLC_Conveyor1"
            }
            mqtt_client.publish("warehouse/events/sensor", json.dumps(message))
            logger.info("[Gateway] 📡 Published MQTT event: PALLET_ARRIVED")

async def main():
    # 1. Connect MQTT
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
    mqtt_client.loop_start()
    
    # 2. First Principle: Distributed Time (Retry Loop)
    client = Client(url=PLC_URL)
    while True:
        try:
            logger.info(f"Attempting to connect to PLC at {PLC_URL}...")
            await client.connect()
            logger.info("✅ Connected to PLC.")
            break
        except Exception as e:
            logger.warning(f"⚠️ PLC not ready yet. Retrying in 3 seconds...")
            await asyncio.sleep(3)

    try:
        # 3. First Principle: Dynamic Discovery
        # Ask the server what index our namespace URI was assigned!
        ns_idx = await client.get_namespace_index(NAMESPACE_URI)
        logger.info(f"🔍 Found Namespace URI '{NAMESPACE_URI}' at dynamic index: {ns_idx}")
        
        # Find the nodes dynamically using the discovered namespace index
        conveyor = await client.nodes.objects.get_child(f"{ns_idx}:Conveyor1")
        sensor_node = await conveyor.get_child(f"{ns_idx}:Sensor_Dock3")
        
        # 4. Create Subscription
        handler = MySubHandler()
        sub = await client.create_subscription(100, handler) 
        await sub.subscribe_data_change(sensor_node)
        
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