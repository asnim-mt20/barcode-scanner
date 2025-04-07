# LIST SERVICES CODE BELOW to get uuid of the scanner
import asyncio
from bleak import BleakClient

SCANNER_MAC_ADDRESS = "AA:FC:4A:1C:10:35"  

async def list_services():
    async with BleakClient(SCANNER_MAC_ADDRESS) as client:
        print(f"Connected: {client.is_connected}")
        services = await client.get_services()
        for service in services:
            print(f"Service UUID: {service.uuid}")
            for char in service.characteristics:
                print(f"  Characteristic UUID: {char.uuid} - Properties: {char.properties}")

asyncio.run(list_services())
