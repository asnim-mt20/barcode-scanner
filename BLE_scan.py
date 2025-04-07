import asyncio
from bleak import BleakClient, BleakScanner
from datetime import datetime
from conn import get_mongo_collection

# Get MongoDB collection
collection = get_mongo_collection()

# Mapping scanners to names
SCANNER_INFO = {
    "AA:FC:4A:1C:10:35": "Scanner 2",
    "AA:FC:65:5B:11:35": "Scanner 4",
    "AA:FC:4B:5A:10:35": "Scanner 5"
}

# Mapping scanners to stages
SCANNER_STAGE_MAP = {
    "AA:FC:4A:1C:10:35": "Checking",
    "AA:FC:65:5B:11:35": "Ironing",
    "AA:FC:4B:5A:10:35": "Printing"
}

SCANNER_MAC_ADDRESSES = list(SCANNER_INFO.keys())
UUID_RX = "00002aa1-0000-1000-8000-00805f9b34fb"

# Discover active scanners
async def get_active_scanners():
    print("🔍 Scanning for active scanners...")
    devices = await BleakScanner.discover(timeout=10)
    active = [d.address for d in devices if d.address in SCANNER_MAC_ADDRESSES]
    print(f"✅ Found {len(active)} active scanner(s): {active}")
    return active

# Handle data from a single scanner
async def handle_scanner(mac):
    scanner_name = SCANNER_INFO.get(mac, "Unknown Scanner")
    stage = SCANNER_STAGE_MAP.get(mac, "Unknown Stage")
    
    try:
        async with BleakClient(mac) as client:
            if client.is_connected:
                print(f"🔗 Connected to {scanner_name} ({mac})")
                data_buffer = []

                def notification_handler(sender, data):
                    decoded = data.decode().strip()
                    print(f"[{scanner_name}] ➜ {decoded}")
                    data_buffer.append(decoded)

                await client.start_notify(UUID_RX, notification_handler)
                await asyncio.sleep(10)
                await client.stop_notify(UUID_RX)

                if data_buffer:
                    for raw_entry in data_buffer:
                        order_id = raw_entry.split("-")[0]
                        timestamp = datetime.now()

                        existing = collection.find_one({"order_id": order_id})
                        if existing:
                            duplicate_count = existing.get("duplicate_count", 1) + 1
                            entries = existing.get("entries", [])
                            entries.append({
                                "stage": stage,
                                "scanned_by": scanner_name,
                                "timestamp": timestamp
                            })
                            collection.update_one(
                                {"order_id": order_id},
                                {
                                    "$set": {
                                        "current_stage": stage,
                                        "duplicate_count": duplicate_count,
                                        "entries": entries
                                    }
                                }
                            )
                        else:
                            doc = {
                                "order_id": order_id,
                                "duplicate_count": 1,
                                "current_stage": stage,
                                "entries": [
                                    {
                                        "stage": stage,
                                        "scanned_by": scanner_name,
                                        "timestamp": timestamp
                                    }
                                ]
                            }
                            collection.insert_one(doc)
                    print(f"✅ All data from {scanner_name} processed and saved.")
                else:
                    print(f"⚠️ No data received from {scanner_name}")
    except Exception as e:
        print(f"❌ Error with {scanner_name}: {e}")

# Main scanner loop
async def main():
    active_macs = await get_active_scanners()
    if not active_macs:
        print("❌ No known scanners found nearby.")
        return
    await asyncio.gather(*(handle_scanner(mac) for mac in active_macs))

# CLI loop
if __name__ == "__main__":
    while True:
        command = input("\nType 'start' to upload scans or 'exit' to quit:\n").strip().lower()
        if command == 'start':
            asyncio.run(main())
        elif command == 'exit':
            print("👋 Exiting scanner interface.")
            break
        else:
            print("⚠️ Unknown command.")
