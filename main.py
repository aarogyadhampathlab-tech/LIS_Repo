import sys
from qt_gui import LabApp, create_application
from network_watcher import start_sync_task, start_observer

class ActivityLogWriter:
    def __init__(self, app):
        self.app = app

    def write(self, text):
        self.app.queue_activity_text(text)
        return len(text)

    def flush(self):
        pass

def main():
    application = create_application(sys.argv)
    app = LabApp()
    log_writer = ActivityLogWriter(app)
    original_stdout, original_stderr = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = log_writer

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
        sys.stdout, sys.stderr = original_stdout, original_stderr

if __name__ == "__main__":
    main()
