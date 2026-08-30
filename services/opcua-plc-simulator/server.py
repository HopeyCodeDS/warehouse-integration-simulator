import asyncio
import logging
from asyncua import Server, ua
from asyncua.common.methods import uamethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PLC-Simulator")

async def main():
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

    # Make variables writable so the Gateway or HMI can control them
    await running_var.set_writable()
    await speed_var.set_writable()

    logger.info("Starting OPC UA Server on port 4840...")
    async with server:
        # 4. Simulation Loop (The "Physics" of the PLC)
        while True:
            is_running = await running_var.read_value()
            
            if is_running:
                logger.info("[PLC] Conveyor is RUNNING. Simulating movement...")
                # Explicitly write as Float (32-bit REAL), matching the tag declaration
                await speed_var.write_value(0.8, ua.VariantType.Float)
                
                await asyncio.sleep(4)
                
                logger.info("[PLC] 🟢 Pallet arrived at Dock 3 Sensor!")
                await sensor_var.write_value(True)   # Boolean, no cast needed
                await asyncio.sleep(1)
                await sensor_var.write_value(False)
                
                await running_var.write_value(False)  # Boolean, no cast needed
                # Explicitly write as Float
                await speed_var.write_value(0.0, ua.VariantType.Float)
                logger.info("[PLC] Conveyor STOPPED.")
            else:
                await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(main())