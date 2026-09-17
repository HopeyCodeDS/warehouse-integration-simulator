import asyncio
import logging
import json
import os
import paho.mqtt.client as mqtt
from asyncua import Server, ua
from asyncua.common.methods import uamethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PLC-Simulator")

MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))

async def main():
    loop = asyncio.get_running_loop()
    tick_event = asyncio.Event()
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="plc-simulator")
    mqtt_client.on_message = lambda client, userdata, message: loop.call_soon_threadsafe(tick_event.set)
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
    mqtt_client.subscribe("warehouse/simulation/tick")
    mqtt_client.loop_start()
    # 1. Setup Server
    server = Server()
    await server.init()
    server.set_endpoint('opc.tcp://0.0.0.0:4840/freeopcua/server/')
    server.set_server_name("WIS PLC Simulator")

    # 2. Setup Namespace
    uri = "http://examples.freeopcua.github.io"
    idx = await server.register_namespace(uri)

    # 3. Create Object Model (The "Digital Twin" of the Conveyor)
    # In a real PLC, this is the "Tags" folder.
    myobj = await server.nodes.objects.add_object(idx, "Conveyor1")
    
    # Add Variables (Tags)
    # First Principle: Industrial data types. We use Boolean and Float.
    running_var = await myobj.add_variable(idx, "Running", False, varianttype=ua.VariantType.Boolean)
    speed_var = await myobj.add_variable(idx, "Speed", 0.0, varianttype=ua.VariantType.Float)
    sensor_var = await myobj.add_variable(idx, "Sensor_Dock3", False, varianttype=ua.VariantType.Boolean)
    occupied_var = await myobj.add_variable(idx, "Occupied", False, varianttype=ua.VariantType.Boolean)
    direction_var = await myobj.add_variable(idx, "Direction", "FORWARD", varianttype=ua.VariantType.String)
    pallet_var = await myobj.add_variable(idx, "PalletId", "", varianttype=ua.VariantType.String)
    jam_var = await myobj.add_variable(idx, "Jam", False, varianttype=ua.VariantType.Boolean)

    # Make variables writable so the Gateway or HMI can control them
    await running_var.set_writable()
    await speed_var.set_writable()

    logger.info("Starting OPC UA Server on port 4840...")
    async with server:
        # 4. Simulation Loop (The "Physics" of the PLC)
        while True:
            await tick_event.wait()
            tick_event.clear()
            is_running = await running_var.read_value()
            is_jammed = await jam_var.read_value()
            
            if is_running and not is_jammed:
                logger.info("[PLC] Conveyor is RUNNING. Simulating movement...")
                # Explicitly write as Float (32-bit REAL), matching the tag declaration
                await speed_var.write_value(0.8, ua.VariantType.Float)
                
                await occupied_var.write_value(True)
                await pallet_var.write_value("PALLET-DEMO-001")
                
                logger.info("[PLC] 🟢 Pallet arrived at Dock 3 Sensor!")
                await sensor_var.write_value(True)   # Boolean, no cast needed
                await sensor_var.write_value(False)
                await occupied_var.write_value(False)
                await pallet_var.write_value("")
                
                await running_var.write_value(False)  # Boolean, no cast needed
                # Explicitly write as Float
                await speed_var.write_value(0.0, ua.VariantType.Float)
                logger.info("[PLC] Conveyor STOPPED.")
            elif is_jammed:
                await speed_var.write_value(0.0, ua.VariantType.Float)
                continue

    mqtt_client.loop_stop()
    mqtt_client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())