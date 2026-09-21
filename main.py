import tkinter as tk
from gui import LabApp
from network_watcher import start_sync_task, start_observer

def main():
    # 1. Initialize the main window
    root = tk.Tk()
    app = LabApp(root)

    # 2. Start the Network Sync Task
    # We pass 'app.update_network_status' so the background thread 
    # can update the green/red dot in the UI.
    start_sync_task(app.update_network_status)

    # 3. Start the Folder Watcher
    # When a new file is found, it will call 'app.add_records' 
    # to display the data in the table.
    observer = start_observer(app.add_records)

    try:
        # 4. Run the Application
        root.mainloop()
    finally:
        # Ensure the background watcher stops when you close the app
        observer.stop()
        observer.join()

if __name__ == "__main__":
    main()
