import asyncio
from bleak import BleakScanner

async def scan():
    devices = await BleakScanner.discover()
    for device in devices:
        print(f"Name: {device.name}, Address: {device.address}")

asyncio.run(scan())

# Name: BarCode Bluetooth BLE, Address: AA:FC:4B:5A:10:35 - Scanner 5
# Name: BarCode Bluetooth BLE, Address: AA:FC:65:5B:11:35 - Scanner 4
# Name: BarCode Bluetooth BLE, Address: AA:FC:4A:1C:10:35 - Scanner 2


