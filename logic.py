# Save this as logic.py
import time, os
from watchdog.events import FileSystemEventHandler
from config import TEST_MAP, NETWORK_SOURCE

class FileProcessor(FileSystemEventHandler):
    def __init__(self, ui_handle):
        self.ui = ui_handle

    def on_created(self, event):
        if event.is_directory: return
        time.sleep(1.5) # Wait for file to finish writing
        
        valid_rows = []
        try:
            with open(event.src_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parts = [p.strip() for p in line.split('\t')]
                    if len(parts) >= 6:
                        name, tid, res = parts[1], parts[4], parts[5]
                        if any(c.isalpha() for c in name) and "No Result" not in res:
                            test_name = TEST_MAP.get(tid, f"ID: {tid}")
                            valid_rows.append((name, test_name, res))
            
            if valid_rows:
                # Tell the UI to show the new data
                self.ui.root.after(0, lambda: self.ui.add_records(valid_rows))
        except Exception as e:
            print(f"Error: {e}")

def check_network(ui):
    while True:
        status = os.path.exists(NETWORK_SOURCE)
        msg = f"CONNECTED: {NETWORK_SOURCE}" if status else "OFFLINE - CHECK NETWORK"
        ui.root.after(0, lambda: ui.update_status(status, msg))
        time.sleep(10)
