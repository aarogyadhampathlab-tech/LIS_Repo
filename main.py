import sys

from GUI.main_gui import LabApp, create_application
from core.network_watcher import start_sync_task, start_observer

def main():
    application = create_application(sys.argv)
    app = LabApp()
    observer = None
    try:
        start_sync_task(app.update_network_status)
        observer = start_observer(app.add_records)
        app.show()
        return application.exec()
    finally:
        if observer is not None:
            observer.stop()
            observer.join()

if __name__ == "__main__":
    main()
