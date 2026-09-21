import re
import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os
import time
import winsound
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# NOTE: Ensure you have a 'config.py' with REPORT_PATH defined, 
# or replace REPORT_PATH below with a string like "report.csv"
try:
    from config import REPORT_PATH, CRITICAL_RANGES, TECHNICAL_ERROR_KEYWORDS
except ImportError:
    REPORT_PATH = "lab_reports.csv"
    CRITICAL_RANGES = {}
    TECHNICAL_ERROR_KEYWORDS = []

# --- 1. NOTIFICATION MANAGER ---
class NotificationManager:
    def __init__(self):
        self.notifications = []
        self.notification_window = None
        self.drag_data = {"x": 0, "y": 0}

    def show(self, patient_name, test_name, result, a1c_result=None, root=None):
        """Add a new notification and display all stacked."""
        # 🔊 Play Urgent Sound
        winsound.PlaySound("SystemHand", winsound.SND_ALIAS | winsound.SND_ASYNC)

        # Add to list
        self.notifications.append({
            'patient': patient_name,
            'test': test_name,
            'result': result,
            'a1c': a1c_result
        })

        # Refresh the notification window
        if root:
            self._refresh_window(root)

    def _on_drag_start(self, event):
        """Start dragging the notification window."""
        self.drag_data["x"] = event.x_root - self.notification_window.winfo_x()
        self.drag_data["y"] = event.y_root - self.notification_window.winfo_y()

    def _on_drag_motion(self, event):
        """Handle dragging motion of notification window."""
        x = event.x_root - self.drag_data["x"]
        y = event.y_root - self.drag_data["y"]
        self.notification_window.geometry(f"+{x}+{y}")

    def _refresh_window(self, root):
        """Create/update the notification window with all active notifications stacked."""
        # Destroy old window if it exists
        if self.notification_window:
            self.notification_window.destroy()

        # Create new window
        self.notification_window = tk.Toplevel(root)
        self.notification_window.overrideredirect(True)
        self.notification_window.attributes("-topmost", True)
        self.notification_window.configure(bg="#0f172a")

        # Main container
        main_frame = tk.Frame(self.notification_window, bg="#0f172a")
        main_frame.pack(fill='both', expand=True)

        # Add each notification
        for idx, notif in enumerate(self.notifications):
            self._add_notification_item(main_frame, idx, notif)

        # Position Bottom-Left
        self.notification_window.update_idletasks()
        w = self.notification_window.winfo_width()
        h = self.notification_window.winfo_height()
        sh = self.notification_window.winfo_screenheight()
        self.notification_window.geometry(f"{w}x{h}+20+{sh - h - 70}")

        # Bind drag events to the main frame for draggability
        main_frame.bind("<Button-1>", self._on_drag_start)
        main_frame.bind("<B1-Motion>", self._on_drag_motion)

    def _add_notification_item(self, parent, idx, notif):
        """Add a single notification item with close button and optional A1C."""
        # Notification frame
        item_frame = tk.Frame(parent, bg="#1e293b")
        item_frame.pack(fill='x', padx=5, pady=5)

        # Header with patient and test info
        header = tk.Frame(item_frame, bg="#1e293b")
        header.pack(fill='x', padx=8, pady=5)

        # Left side: Patient, Test, Glucose, and A1C all in one row
        info_text = f"👤 {notif['patient']} | 🧪 {notif['test']} | 📊 {notif['result']}"
        if notif['a1c']:
            info_text += f" | 🩸 A1C: {notif['a1c']}"
        
        tk.Label(header, text=info_text, fg="white", bg="#1e293b", 
                 font=("Segoe UI", 9, "bold"), wraplength=500, justify='left').pack(side=tk.LEFT, expand=True, anchor='w')

        # Close button
        close_btn = tk.Label(header, text="✕", fg="#94a3b8", bg="#1e293b", 
                             font=("Arial", 10, "bold"), cursor="hand2")
        close_btn.pack(side=tk.RIGHT, padx=5)
        close_btn.bind("<Button-1>", lambda e, i=idx: self._close_notification(i))

    def _close_notification(self, idx):
        """Close a specific notification and refresh."""
        if 0 <= idx < len(self.notifications):
            self.notifications.pop(idx)
            if self.notifications and self.notification_window:
                root = self.notification_window.master
                self._refresh_window(root)
            elif self.notification_window:
                self.notification_window.destroy()
                self.notification_window = None


# Global notification manager
notification_manager = NotificationManager()

# --- 2. FOLDER WATCHER HANDLER ---
class FolderWatcher(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app

    def on_created(self, event):
        if not event.is_directory:
            file_name = os.path.basename(event.src_path)
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] NEW FILE DETECTED: {file_name}")
            # You can trigger a UI update here if needed

# --- 3. MAIN APPLICATION ---
class LabApp:
    def __init__(self, root):
        self.root = root
        self.root.title(" Lab Monitor Pro 🧬")
        self.root.geometry("1000x850")
        self.root.configure(bg="#0f172a")
        self.root.attributes("-topmost", True)
        
        self.all_records = []
        self.notified_records = set()  # Track which records have been notified
        self.alerted_records = set()   # Track which critical alerts have already fired
        self._setup_styles()
        self._build_glossy_header()
        self._build_status_bar()
        self._build_filters()
        self._build_table()
        self._build_context_menu()
        self._build_buttons()

        # Start Folder Watching (Update this path to your needs)
        self.start_folder_watch("./") 

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#1e293b", foreground="#e2e8f0", 
                        rowheight=40, fieldbackground="#1e293b", borderwidth=0, 
                        font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background="#334155", foreground="#38bdf8", 
                        font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("Treeview", background=[('selected', '#0ea5e9')])

    def _build_glossy_header(self):
        tk.Frame(self.root, bg="#0ea5e9", height=4).pack(fill='x')
        header = tk.Frame(self.root, bg="#1e293b", height=80)
        header.pack(fill='x')
        title_frame = tk.Frame(header, bg="#1e293b")
        title_frame.pack(side=tk.LEFT, padx=30, pady=15)
        tk.Label(title_frame, text="LAB AUTOMATION", fg="#38bdf8", bg="#1e293b",
                 font=("Segoe UI", 18, "bold")).pack(anchor='w')
        tk.Label(title_frame, text="ADVANCED ANALYTICS SYSTEM", fg="#94a3b8", 
                 bg="#1e293b", font=("Segoe UI", 8, "bold")).pack(anchor='w')

    def _build_status_bar(self):
        self.status_frame = tk.Frame(self.root, bg="#0f172a")
        self.status_frame.pack(fill='x', padx=30, pady=10)
        self.status_dot = tk.Label(self.status_frame, text="●", fg="#ef4444", 
                                   font=("Arial", 14), bg="#0f172a")
        self.status_dot.pack(side=tk.LEFT)
        self.status_text = tk.Label(self.status_frame, text="SYSTEM OFFLINE", 
                                    fg="#ef4444", font=("Segoe UI", 9, "bold"), bg="#0f172a")
        self.status_text.pack(side=tk.LEFT, padx=8)
        self.alert_text = tk.Label(self.status_frame, text="", 
                                   fg="#facc15", font=("Segoe UI", 9, "bold"), bg="#0f172a")
        self.alert_text.pack(side=tk.RIGHT)

    def _build_filters(self):
        filter_container = tk.Frame(self.root, bg="#0f172a")
        filter_container.pack(fill='x', padx=30, pady=5)
        
        # Patient Search
        p_frame = tk.Frame(filter_container, bg="#1e293b", padx=10, pady=5)
        p_frame.pack(side=tk.LEFT, expand=True, fill='x', padx=(0, 5))
        tk.Label(p_frame, text="👤 Patient:", fg="#38bdf8", bg="#1e293b", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)
        self.search_pat = tk.StringVar()
        self.search_pat.trace_add("write", self.filter_data)
        tk.Entry(p_frame, textvariable=self.search_pat, bg="#0f172a", fg="white", borderwidth=0, insertbackground="white").pack(side=tk.LEFT, padx=10, fill='x', expand=True)

        # Test Search
        t_frame = tk.Frame(filter_container, bg="#1e293b", padx=10, pady=5)
        t_frame.pack(side=tk.LEFT, expand=True, fill='x', padx=(5, 0))
        tk.Label(t_frame, text="🧪 Test:", fg="#38bdf8", bg="#1e293b", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)
        self.search_test = tk.StringVar()
        self.search_test.trace_add("write", self.filter_data)
        tk.Entry(t_frame, textvariable=self.search_test, bg="#0f172a", fg="white", borderwidth=0, insertbackground="white").pack(side=tk.LEFT, padx=10, fill='x', expand=True)

    def _build_table(self):
        table_frame = tk.Frame(self.root, bg="#334155", padx=1, pady=1)
        table_frame.pack(expand=True, fill='both', padx=30, pady=10)
        cols = ('Test Name', 'Result')
        self.tree = ttk.Treeview(table_frame, columns=cols, show='tree headings', selectmode="extended")
        self.tree.heading('#0', text='PATIENT LIST (Right-click to Delete)')
        self.tree.heading('Test Name', text='TEST TYPE')
        self.tree.heading('Result', text='RESULT')
        self.tree.column('#0', width=400)
        self.tree.pack(expand=True, fill='both')
        self.tree.bind("<Button-3>", self._show_context_menu)

    def _build_context_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0, bg="#1e293b", fg="white")
        self.menu.add_command(label="❌ Delete Selected Patient", command=self.delete_individual)

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.menu.post(event.x_root, event.y_root)

    def _build_buttons(self):
        btn_frame = tk.Frame(self.root, bg="#0f172a")
        btn_frame.pack(pady=20)
        tk.Button(btn_frame, text="SAVE & CLEAR REPORT", bg="#064e3b", fg="#6ee7b7", 
                  font=("Segoe UI", 9, "bold"), relief="flat", command=self.save_to_csv, 
                  padx=30, pady=10, cursor="hand2").pack()

    def filter_data(self, *args):
        for i in self.tree.get_children(): self.tree.delete(i)
        p_query = self.search_pat.get().lower()
        t_query = self.search_test.get().lower()
        
        grouped = {}
        for name, test, res in self.all_records:
            if p_query in name.lower() and t_query in test.lower():
                if name not in grouped: grouped[name] = []
                grouped[name].append((test, res))
        
        for patient_name, tests in grouped.items():
            # 🕒 FEATURE: Time added to Patient Row
            entry_time = time.strftime("%H:%M:%S")
            parent = self.tree.insert("", "end", text=f" [{entry_time}] 👤 {patient_name}", open=False)
            
            glucose_result = None
            a1c_result = None
            
            for t_name, t_res in tests:
                self.tree.insert(parent, "end", values=(t_name, t_res))
                
                # Capture glucose value
                if "glucose" in t_name.lower():
                    glucose_result = t_res
                
                # Capture A1C value (check multiple A1C test name variations)
                if any(a1c_term in t_name.lower() for a1c_term in ["a1c", "hba1c", "derived"]):
                    a1c_result = t_res
            
            # 🔔 FEATURE: Glucose Alert with A1C (ONLY for NEW records)
            if glucose_result:
                record_key = (patient_name, "glucose", glucose_result)  # Unique identifier
                if record_key not in self.notified_records:
                    notification_manager.show(patient_name, "GLUCOSE", glucose_result, a1c_result, self.root)
                    self.notified_records.add(record_key)  # Mark as notified

    def add_records(self, records):
        for rec in records:
            self.all_records.append(rec)
            self._check_record_alert(*rec)
        self.filter_data()
        self.root.bell()

    def _extract_numeric_result(self, result):
        if not result:
            return None

        cleaned = result.replace(',', '.').strip()
        match = re.search(r"[+-]?\d+(?:\.\d+)?", cleaned)
        if not match:
            return None

        try:
            return float(match.group())
        except ValueError:
            return None

    def _is_technical_error(self, result):
        if not result:
            return False

        lowered = result.strip().lower()
        return any(keyword in lowered for keyword in TECHNICAL_ERROR_KEYWORDS)

    def _update_alert_status(self, text):
        self.alert_text.config(text=text, fg="#f87171")
        self.root.after(10000, lambda: self.alert_text.config(text=""))

    def _show_alert(self, patient_name, test_name, result, alert_reason):
        full_title = f"{alert_reason}: {test_name}"
        # Play alert sound and update status, but do NOT show in left notifications
        winsound.PlaySound("SystemHand", winsound.SND_ALIAS | winsound.SND_ASYNC)
        self._update_alert_status(f"{patient_name} | {test_name} → {alert_reason}")

    def _check_record_alert(self, patient_name, test_name, result):
        alert_key = (patient_name, test_name, result)
        if alert_key in self.alerted_records:
            return

        if self._is_technical_error(result):
            self._show_alert(patient_name, test_name, result, "TECHNICAL ERROR")
            self.alerted_records.add(alert_key)
            return

        numeric = self._extract_numeric_result(result)
        if numeric is None:
            return

        range_def = CRITICAL_RANGES.get(test_name)
        if not range_def:
            return

        low = range_def.get("low")
        high = range_def.get("high")

        if low is not None and numeric < low:
            self._show_alert(patient_name, test_name, result, f"LOW (< {low})")
            self.alerted_records.add(alert_key)
            return

        if high is not None and numeric > high:
            self._show_alert(patient_name, test_name, result, f"HIGH (> {high})")
            self.alerted_records.add(alert_key)
            return

    def update_network_status(self, online, path):
        """Update the network status indicator in the UI."""
        if online:
            self.status_dot.config(fg="#22c55e")  # Green
            self.status_text.config(text="SYSTEM ONLINE", fg="#22c55e")
        else:
            self.status_dot.config(fg="#ef4444")  # Red
            self.status_text.config(text="SYSTEM OFFLINE", fg="#ef4444")

    def delete_individual(self):
        selected = self.tree.selection()
        if not selected: return
        # Logic to extract name even with the timestamp prefix
        item_text = self.tree.item(selected[0])['text']
        raw_name = item_text.split("👤")[-1].strip()
        # Remove from both records and notification tracking
        self.all_records = [r for r in self.all_records if r[0] != raw_name]
        self.notified_records = {record for record in self.notified_records if record[0] != raw_name}
        self.filter_data()

    def start_folder_watch(self, path):
        event_handler = FolderWatcher(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, path, recursive=False)
        self.observer.start()

    def save_to_csv(self):
        if not self.all_records: return
        try:
            with open(REPORT_PATH, 'a', newline='') as f:
                writer = csv.writer(f)
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                for rec in self.all_records: writer.writerow([ts] + list(rec))
            self.all_records = []
            self.notified_records = set()  # Clear notification tracking after saving
            self.filter_data()
            messagebox.showinfo("Success", "Report Saved Successfully")
        except Exception as e: 
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = LabApp(root)
    
    # TEST DATA: Uncomment to test the glucose alert on startup
    # app.add_records([("John Doe", "Glucose", "120 mg/dL")])
    
    root.mainloop()
