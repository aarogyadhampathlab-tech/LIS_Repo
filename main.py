# Save this as main.py
import threading
from watchdog.observers import Observer
from interface import LabMonitorUI
from logic import FileProcessor, check_network
from config import WATCH_FOLDER

if __name__ == "__main__":
    # Start the Interface
    app = LabMonitorUI()

    # Start the Folder Watcher
    handler = FileProcessor(app)
    observer = Observer()
    observer.schedule(handler, WATCH_FOLDER, recursive=False)
    observer.start()

    # Start Network Check in background
    threading.Thread(target=check_network, args=(app,), daemon=True).start()

    # Run the App
    try:
        app.run()
    finally:
        observer.stop()
        observer.join()
