import asyncio
import threading
import tkinter as tk
from tkinter import scrolledtext
from bleak import BleakClient, BleakScanner
from datetime import datetime
from conn import get_mongo_collection

collection = get_mongo_collection()

SCANNER_INFO = {
    "AA:FC:8C:18:12:33": "Scanner 1",
    "AA:FC:8D:4C:11:35": "Scanner 2",
    "AA:FC:8E:56:11:35": "Scanner 3",
    "AA:FC:4B:5A:10:35": "Scanner 4",
    "AA:FC:4A:1C:10:35": "Scanner 5",
    "AA:FC:65:5B:11:35": "Scanner 6"
}

SCANNER_STAGE_MAP = {
    "AA:FC:8C:18:12:33": "Checking",
    "AA:FC:8D:4C:11:35": "Sewing_1",
    "AA:FC:8E:56:11:35": "Tailoring",
    "AA:FC:4B:5A:10:35": "Ironing",
    "AA:FC:4A:1C:10:35": "Sewing_2",
    "AA:FC:65:5B:11:35": "Sewing_3"
}

SCANNER_PERSON_MAP = {
    "AA:FC:8C:18:12:33": "Alpa",
    "AA:FC:8D:4C:11:35": "Asgar",
    "AA:FC:8E:56:11:35": "Jatin",
    "AA:FC:4B:5A:10:35": "Ramesh",
    "AA:FC:4A:1C:10:35": "Zakhir",
    "AA:FC:65:5B:11:35": "Sharif"
}

STAGE_SEQUENCE = ["Tailoring","Sewing_1","Sewing_2","Sewing_3","Checking","Ironing"]


SCANNER_MAC_ADDRESSES = list(SCANNER_INFO.keys())
UUID_RX = "00002aa1-0000-1000-8000-00805f9b34fb"

root = tk.Tk()
root.title("Order Status Upload")
root.geometry("700x600")

button_frame = tk.Frame(root)
button_frame.pack(side='top', anchor='n', pady=10)

start_button = tk.Button(button_frame, text="Start Scanning", bg="green", fg="white", font=("Helvetica", 12, "bold"), width=15, height=2)
exit_button = tk.Button(button_frame, text="Exit", bg="red", fg="white", font=("Helvetica", 12, "bold"), width=15, height=2)

start_button.pack(side='left', padx=20)
exit_button.pack(side='left', padx=10)

# Font size increased to 12 and made bold
log_output = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Yu Gothic UI", 13, "bold"))
log_output.pack(expand=True, fill='both')
log_output.configure(state='disabled')

# tag logs config
log_output.tag_config("green", foreground="green", font=("Yu Gothic UI", 12, "bold"))
log_output.tag_config("deepred", foreground="#B22222", font=("Yu Gothic UI", 12, "bold"))
log_output.tag_config("sky", foreground="#00BFFF", font=("Yu Gothic UI", 12, "bold"))
log_output.tag_config("gray", foreground="#6E6E6E", font=("Yu Gothic UI", 12, "italic"))
log_output.tag_config("bold", font=("Yu Gothic UI", 12, "bold")) 


def log(message, color="black"):
    log_output.configure(state='normal')
    log_output.insert(tk.END, message + "\n\n", color)
    log_output.configure(state='disabled')
    log_output.see(tk.END)

async def get_active_scanners():
    log("🔍 Scanning for active scanners...", "sky")
    devices = await BleakScanner.discover(timeout=10)
    active = [d.address for d in devices if d.address in SCANNER_MAC_ADDRESSES]
    log(f"✅ Found {len(active)} active scanner(s): {active}", "green")
    return active

async def handle_scanner(mac):
    scanner_name = SCANNER_INFO.get(mac, "Unknown Scanner")
    stage = SCANNER_STAGE_MAP.get(mac, "Unknown Stage")
    person_name = SCANNER_PERSON_MAP.get(mac, "Unknown")

    try:
        async with BleakClient(mac) as client:
            if client.is_connected:
                log(f"🟢 {person_name} ({scanner_name}) connected for '{stage}'", "green")
                log("Upload with STEP 1 now... ", "sky")
                data_buffer = []

                def notification_handler(sender, data):
                    decoded = data.decode().strip()
                    log(f"[{scanner_name}] ➜ {decoded}", "bold")
                    data_buffer.append(decoded)

                await client.start_notify(UUID_RX, notification_handler)
                await asyncio.sleep(10)
                await client.stop_notify(UUID_RX)

                if data_buffer:
                    for raw_entry in data_buffer:
                        order_id = raw_entry
                        timestamp = datetime.now()

                        existing = collection.find_one({"order_id": order_id})
                        entry_data = {
                            stage:{
                            "scanning_device": scanner_name,
                            "scanned_by": person_name,
                            "timestamp": timestamp
                            }
                        }

                        if existing:
                            duplicate_count = existing.get("duplicate_count", 1) + 1
                            entries = existing.get("entries", [])
                            entries.append(entry_data)

                            # Gather all stages scanned so far
                            scanned_stages = []
                            for entry in entries:
                                if isinstance(entry, dict):
                                    if "stage" in entry:  # old format
                                        scanned_stages.append(entry["stage"])
                                    else:  # new format: {stage_name: {details}}
                                        scanned_stages.extend(entry.keys())

                            # Filter out invalid stages just in case
                            valid_stages = [s for s in scanned_stages if s in STAGE_SEQUENCE]

                            # Determine the farthest stage according to the defined order
                            current_stage = max(valid_stages, key=lambda s: STAGE_SEQUENCE.index(s)) if valid_stages else stage

                            collection.update_one(
                                {"order_id": order_id},
                                {
                                    "$set": {
                                        "current_stage": current_stage,
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

                    log(f"✅ Upload complete from {person_name}\n", "green")
                else:
                    log(f"⚠️ No data received from {person_name}", "deepred")
    except Exception as e:
        log(f"❌ Error with {scanner_name} by {person_name}: {e}", "deepred")

async def main():
    active_macs = await get_active_scanners()
    if not active_macs:
        log("❌ No scanners found nearby. Click start again.", "deepred")
        return
    await asyncio.gather(*(handle_scanner(mac) for mac in active_macs))

def run_async_main():
    asyncio.run(main())

def on_start():
    threading.Thread(target=run_async_main).start()

def on_exit():
    root.destroy()

start_button.config(command=on_start)
exit_button.config(command=on_exit)

root.mainloop()