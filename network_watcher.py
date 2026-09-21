import os
import time
import shutil
import datetime
import subprocess
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import NETWORK_SOURCE, WATCH_FOLDER
from parser_logic import process_file

class MedicalHandler(FileSystemEventHandler):
    """Listens for new files and tells the GUI to update."""
    def __init__(self, ui_callback):
        self.ui_callback = ui_callback
        self.last_processed = {}  # Track file sizes to detect real modifications

    def on_created(self, event):
        if event.is_directory:
            return
        
        # Wait for file to be completely written (check file size stability)
        file_path = event.src_path
        file_name = os.path.basename(file_path)
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] FILE DETECTED: {file_name} - Waiting for write to complete...")
        
        prev_size = 0
        stable_count = 0
        
        while stable_count < 2:  # File must have same size for 2 checks
            try:
                if os.path.exists(file_path):
                    curr_size = os.path.getsize(file_path)
                    if curr_size == prev_size and curr_size > 0:
                        stable_count += 1
                    else:
                        stable_count = 0
                    prev_size = curr_size
            except:
                pass
            time.sleep(0.2)  # Check every 200ms instead of sleeping blindly
        
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] FILE READY: {file_name} - Processing ({prev_size} bytes)...")
        
        # Parse the new file using our parser logic
        new_data = process_file(file_path)
        
        # If we found valid test results, send them to the GUI
        if new_data:
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] ✅ DATA SENT TO GUI: {len(new_data)} test results from {file_name}")
            self.last_processed[file_path] = prev_size
            self.ui_callback(new_data)
    
    def on_modified(self, event):
        """Handle file modifications (when new data is added)."""
        if event.is_directory:
            return
        
        file_path = event.src_path
        file_name = os.path.basename(file_path)
        
        try:
            curr_size = os.path.getsize(file_path)
            last_size = self.last_processed.get(file_path, 0)
            
            # Only process if file grew (new data added)
            if curr_size > last_size:
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] FILE MODIFIED: {file_name} - Size increased ({last_size} → {curr_size} bytes)")
                
                # Wait for write to stabilize
                time.sleep(0.5)
                prev_size = curr_size
                stable_count = 0
                
                while stable_count < 2:
                    try:
                        if os.path.exists(file_path):
                            new_size = os.path.getsize(file_path)
                            if new_size == prev_size:
                                stable_count += 1
                            else:
                                stable_count = 0
                            prev_size = new_size
                    except:
                        pass
                    time.sleep(0.2)
                
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] FILE READY (MODIFIED): {file_name} - Reprocessing ({prev_size} bytes)...")
                
                # Reprocess the updated file
                new_data = process_file(file_path)
                
                if new_data:
                    ts = datetime.datetime.now().strftime("%H:%M:%S")
                    print(f"[{ts}] ✅ UPDATED DATA SENT TO GUI: {len(new_data)} test results from {file_name}")
                    self.last_processed[file_path] = prev_size
                    self.ui_callback(new_data)
        except Exception as e:
            print(f"Error in on_modified for {file_name}: {e}")

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
    return observer
