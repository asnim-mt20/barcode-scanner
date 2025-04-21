import asyncio
from bleak import BleakClient, BleakScanner
from datetime import datetime
from conn import get_mongo_collection

collection = get_mongo_collection()

# MAC to Scanner Name
SCANNER_INFO = {
    "AA:FC:8C:18:12:33": "Scanner 1",
    "AA:FC:8D:4C:11:35": "Scanner 2", 
    "AA:FC:8E:56:11:35": "Scanner 3",
    "AA:FC:4B:5A:10:35": "Scanner 4" 
}

# MAC to Stage Mapping
SCANNER_STAGE_MAP = {
    "AA:FC:8C:18:12:33": "Checking",   # Scanner 1
    "AA:FC:8D:4C:11:35": "Sewing",     # Scanner 2
    "AA:FC:8E:56:11:35": "Tailoring",  # Scanner 3
    "AA:FC:4B:5A:10:35": "Ironing"     # Scanner 4
}

# MAC to Person Mapping
SCANNER_PERSON_MAP = {
    "AA:FC:8C:18:12:33": "Alpa",  # Scanner 1
    "AA:FC:8D:4C:11:35": "Asgar", # Scanner 2
    "AA:FC:8E:56:11:35": "Jatin", # Scanner 3
    "AA:FC:4B:5A:10:35": "Ramesh" # Scanner 4
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
    person_name = SCANNER_PERSON_MAP.get(mac, "Unknown")

    try:
        async with BleakClient(mac) as client:
            if client.is_connected:
                print(f"🔗 Connected to {scanner_name} for {stage} ({mac})")
                print(f"📥 Upload Scanned Data Now...")
                data_buffer = []

                def notification_handler(sender, data):
                    decoded = data.decode().strip()
                    print(f"[{scanner_name}] ➜ {decoded}")
                    data_buffer.append(decoded)

                await client.start_notify(UUID_RX, notification_handler)
                await asyncio.sleep(60)  # Wait for scan data to come in
                await client.stop_notify(UUID_RX)

                if data_buffer:
                    for raw_entry in data_buffer:
                        order_id = raw_entry
                        timestamp = datetime.now()

                        existing = collection.find_one({"order_id": order_id})
                        entry_data = {
                            "stage": stage,
                            "scanning_device": scanner_name,
                            "scanned_by": person_name,
                            "timestamp": timestamp
                        }

                        if existing:
                            duplicate_count = existing.get("duplicate_count", 1) + 1
                            entries = existing.get("entries", [])
                            entries.append(entry_data)

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
                                "entries": [entry_data]
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
            print("👋 Exiting scanner interface. Run file again to start.")
            break
        else:
            print("⚠️ Unknown command.")
