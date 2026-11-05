import os
import time
import shutil
import datetime
import subprocess
import threading
from collections import Counter
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import NETWORK_SOURCE, WATCH_FOLDER
from parser_logic import process_file

class MedicalHandler(FileSystemEventHandler):
    """Processes completed LIS result logs and forwards only unseen rows."""
    def __init__(self, ui_callback):
        self.ui_callback = ui_callback
        self.last_processed = {}
        self.file_records = {}
        self.processing_lock = threading.Lock()

    @staticmethod
    def _is_current_result_log(file_path):
        file_name = os.path.basename(file_path).lower()
        today_prefix = datetime.datetime.now().strftime("%m%d%Y").lower()
        return file_name.startswith(today_prefix) and file_name.endswith("r.log")

    def on_created(self, event):
        if event.is_directory or not self._is_current_result_log(event.src_path):
            return
        self._process_when_stable(event.src_path)

    def on_modified(self, event):
        if event.is_directory or not self._is_current_result_log(event.src_path):
            return

        self._process_when_stable(event.src_path)

    def process_existing_files(self, folder_path):
        """Load result logs already present when the watcher starts."""
        try:
            for file_name in sorted(os.listdir(folder_path)):
                file_path = os.path.join(folder_path, file_name)
                if os.path.isfile(file_path) and self._is_current_result_log(file_path):
                    self._process_file(file_path)
        except OSError as error:
            print(f"Error scanning result logs in {folder_path}: {error}")

    def _process_when_stable(self, file_path):
        deadline = time.monotonic() + 15
        previous_signature = None
        stable_count = 0
        try:
            while time.monotonic() < deadline:
                try:
                    stat = os.stat(file_path)
                except FileNotFoundError:
                    return

                signature = (stat.st_size, stat.st_mtime_ns)
                if stat.st_size > 0 and signature == previous_signature:
                    stable_count += 1
                    if stable_count >= 2:
                        self._process_file(file_path)
                        return
                else:
                    stable_count = 0
                previous_signature = signature
                time.sleep(0.2)

            print(f"Result log did not stabilize within 15 seconds: {file_path}")
        except Exception as e:
            print(f"Error waiting for result log {file_path}: {e}")

    def _process_file(self, file_path):
        try:
            stat = os.stat(file_path)
            signature = (stat.st_size, stat.st_mtime_ns)
            with self.processing_lock:
                if self.last_processed.get(file_path) == signature:
                    return

                records = process_file(file_path)
                previous_records = self.file_records.get(file_path, Counter())
                current_records = Counter(records)
                new_records = list((current_records - previous_records).elements())
                self.file_records[file_path] = current_records
                self.last_processed[file_path] = signature

            file_name = os.path.basename(file_path)
            if new_records:
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                print(
                    f"[{timestamp}] DATA SENT TO GUI: {len(new_records)} results "
                    f"from {file_name}"
                )
                self.ui_callback(new_records)
        except Exception as error:
            print(f"Error processing result log {file_path}: {error}")

def start_sync_task(status_callback):
    """Check network connection and copy new logs every 10 seconds."""
    def run():
        while True:
            try:
                # 1. Check if server is reachable (Ping)
                host_ip = "192.168.1.103"
                ping = subprocess.run(f"ping -n 1 -w 1000 {host_ip}", 
                                     stdout=subprocess.DEVNULL, shell=True)
                
                # 2. Check if folder is accessible
                online = os.path.isdir(NETWORK_SOURCE)
                status_callback(online, NETWORK_SOURCE)
                
                if online:
                    today_str = datetime.datetime.now().strftime("%m%d%Y")
                    for f in os.listdir(NETWORK_SOURCE):
                        # Only copy today's result logs
                        if f.startswith(today_str) and f.lower().endswith('r.log'):
                            src = os.path.join(NETWORK_SOURCE, f)
                            dst = os.path.join(WATCH_FOLDER, f)
                            
                            if os.path.isfile(src):
                                # Check if file is new OR has been modified since last copy
                                should_copy = False
                                
                                if not os.path.exists(dst):
                                    # File doesn't exist yet - copy it
                                    should_copy = True
                                else:
                                    # File exists - check if source is newer or larger
                                    src_mtime = os.path.getmtime(src)
                                    dst_mtime = os.path.getmtime(dst)
                                    src_size = os.path.getsize(src)
                                    dst_size = os.path.getsize(dst)
                                    
                                    # Copy if source was modified after destination
                                    # OR if source is larger (more data added)
                                    if src_mtime > dst_mtime or src_size > dst_size:
                                        should_copy = True
                                
                                if should_copy:
                                    shutil.copy2(src, dst)
            except Exception as e:
                print(f"Sync error: {e}")
            
            time.sleep(3)  # Check every 3 seconds instead of 10 for faster detection

    # Run this in a background thread so the GUI doesn't freeze
    threading.Thread(target=run, daemon=True).start()

def start_observer(ui_callback):
    """Starts the watchdog observer to monitor the local folder."""
    if not os.path.exists(WATCH_FOLDER):
        os.makedirs(WATCH_FOLDER)
        
    observer = Observer()
    handler = MedicalHandler(ui_callback)
    observer.schedule(handler, WATCH_FOLDER, recursive=False)
    observer.start()
    threading.Thread(
        target=handler.process_existing_files,
        args=(WATCH_FOLDER,),
        daemon=True,
    ).start()
    return observer
