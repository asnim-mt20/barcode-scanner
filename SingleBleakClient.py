import asyncio
from bleak import BleakClient

SCANNER_MAC_ADDRESS = "AA:FC:65:5B:11:35"
UUID_RX = "00002aa1-0000-1000-8000-00805f9b34fb"  # Replace with the correct UUID from the scan

def notification_handler(sender, data):
    print(f"Received Data: {data.decode()}")

async def receive_notifications():
    async with BleakClient(SCANNER_MAC_ADDRESS) as client:
        if client.is_connected:
            print("Connected to Scanner!")
            await client.start_notify(UUID_RX, notification_handler)

            print("Waiting for barcode data... Scan 'upload all data' now.")
            await asyncio.sleep(30)

            await client.stop_notify(UUID_RX)

asyncio.run(receive_notifications())
