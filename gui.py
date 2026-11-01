import re
import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os
import time
import queue
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

COLORS = {
    "background": "#F3F6F5",
    "surface": "#FFFFFF",
    "surface_alt": "#EAF0EE",
    "border": "#D9E3E0",
    "text": "#263632",
    "muted": "#71817C",
    "accent": "#28796F",
    "accent_hover": "#21675F",
    "accent_soft": "#DCEDE9",
    "online": "#287A55",
    "offline": "#B34D48",
    "warning": "#A66A1C",
}

# --- 1. NOTIFICATION MANAGER ---
class NotificationManager:
    def __init__(self):
        self.notifications = []
        self.notification_window = None
        self.drag_data = {"x": 0, "y": 0}
        self.collapsed = False

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
        self.notification_window.configure(bg=COLORS["background"])

        # Main container
        main_frame = tk.Frame(self.notification_window, bg=COLORS["background"])
        main_frame.pack(fill='both', expand=True)

        toolbar = tk.Frame(main_frame, bg=COLORS["background"])
        toolbar.pack(fill='x', padx=5, pady=(5, 0))
        tk.Label(toolbar, text="GLUCOSE ALERTS", fg=COLORS["accent"], bg=COLORS["background"],
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="+" if self.collapsed else "−",
              command=self._toggle_collapsed, bg=COLORS["surface_alt"], fg=COLORS["text"],
              activebackground=COLORS["border"], activeforeground=COLORS["text"],
              relief="flat", bd=0, font=("Segoe UI", 10, "bold"),
                  width=2, cursor="hand2").pack(side=tk.RIGHT, padx=2)

        # Add each notification
        if not self.collapsed:
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

    def _toggle_collapsed(self):
        self.collapsed = not self.collapsed
        if self.notification_window:
            self._refresh_window(self.notification_window.master)

    def _add_notification_item(self, parent, idx, notif):
        """Add a single notification item with close button and optional A1C."""
        # Notification frame
        item_frame = tk.Frame(parent, bg=COLORS["surface_alt"])
        item_frame.pack(fill='x', padx=5, pady=5)

        # Header with patient and test info
        header = tk.Frame(item_frame, bg=COLORS["surface_alt"])
        header.pack(fill='x', padx=8, pady=5)

        # Left side: Patient, Test, Glucose, and A1C all in one row
        info_text = f"{notif['patient']}  |  {notif['test']}  |  {notif['result']}"
        if notif['a1c']:
            info_text += f"  |  A1C: {notif['a1c']}"
        
        tk.Label(header, text=info_text, fg=COLORS["text"], bg=COLORS["surface_alt"], 
                 font=("Segoe UI", 9, "bold"), wraplength=500, justify='left').pack(side=tk.LEFT, expand=True, anchor='w')

        # Close button
        close_btn = tk.Label(header, text="×", fg=COLORS["muted"], bg=COLORS["surface_alt"], 
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
        self.root.title("LIS Lab Monitor")
        self.root.geometry("1080x820")
        self.root.minsize(800, 620)
        self.root.configure(bg=COLORS["background"])
        self.root.attributes("-topmost", True)
        self.activity_queue = queue.Queue()
        
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
        self._build_activity_log()
        self.root.after(100, self._flush_activity_log)

        # Start Folder Watching (Update this path to your needs)
        self.start_folder_watch("./") 

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=COLORS["surface"], foreground=COLORS["text"],
                        rowheight=34, fieldbackground=COLORS["surface"], borderwidth=0,
                        font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=COLORS["surface_alt"],
                        foreground=COLORS["muted"], font=("Segoe UI", 9, "bold"),
                        borderwidth=0, padding=(10, 9))
        style.map("Treeview", background=[("selected", COLORS["accent_soft"])],
                  foreground=[("selected", COLORS["text"])])
        style.configure("Vertical.TScrollbar", background=COLORS["surface_alt"],
                        troughcolor=COLORS["background"], bordercolor=COLORS["background"],
                        arrowcolor=COLORS["muted"])

    def _build_glossy_header(self):
        header = tk.Frame(self.root, bg=COLORS["surface"], height=88,
                          highlightthickness=1, highlightbackground=COLORS["border"])
        header.pack(fill="x")
        header.pack_propagate(False)
        mark = tk.Canvas(header, width=42, height=42, bg=COLORS["surface"],
                         highlightthickness=0)
        mark.pack(side=tk.LEFT, padx=(28, 12), pady=20)
        mark.create_line(14, 7, 28, 7, 28, 17, 35, 33, 7, 33, 14, 17, 14, 7,
                         fill=COLORS["accent"], width=2, joinstyle="round")
        mark.create_polygon(12, 27, 30, 27, 33, 32, 9, 32,
                            fill=COLORS["accent_soft"], outline="")
        mark.create_line(16, 7, 26, 7, fill=COLORS["accent"], width=2)
        title_frame = tk.Frame(header, bg=COLORS["surface"])
        title_frame.pack(side=tk.LEFT, pady=15)
        tk.Label(title_frame, text="LIS LAB MONITOR", fg=COLORS["text"],
                 bg=COLORS["surface"], font=("Segoe UI Semibold", 16)).pack(anchor="w")
        tk.Label(title_frame, text="LABORATORY RESULTS", fg=COLORS["muted"],
                 bg=COLORS["surface"], font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))

    def _build_status_bar(self):
        self.status_frame = tk.Frame(self.root, bg=COLORS["background"])
        self.status_frame.pack(fill="x", padx=30, pady=(18, 10))
        self.status_dot = tk.Label(self.status_frame, text="●", fg=COLORS["offline"],
                                   font=("Arial", 11), bg=COLORS["background"])
        self.status_dot.pack(side=tk.LEFT)
        self.status_text = tk.Label(self.status_frame, text="OFFLINE",
                                    fg=COLORS["offline"], font=("Segoe UI", 9, "bold"),
                                    bg=COLORS["background"])
        self.status_text.pack(side=tk.LEFT, padx=(6, 8))
        self.alert_text = tk.Label(self.status_frame, text="", fg=COLORS["warning"],
                                   font=("Segoe UI", 9, "bold"), bg=COLORS["background"])
        self.alert_text.pack(side=tk.RIGHT)

    def _build_filters(self):
        filter_container = tk.Frame(self.root, bg=COLORS["background"])
        filter_container.pack(fill="x", padx=30, pady=(4, 10))
        
        p_frame = tk.Frame(filter_container, bg=COLORS["surface"], padx=12, pady=8,
                           highlightthickness=1, highlightbackground=COLORS["border"])
        p_frame.pack(side=tk.LEFT, expand=True, fill="x", padx=(0, 6))
        tk.Label(p_frame, text="PATIENT", fg=COLORS["muted"], bg=COLORS["surface"],
                 font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)
        self.search_pat = tk.StringVar()
        self.search_pat.trace_add("write", self.filter_data)
        tk.Entry(p_frame, textvariable=self.search_pat, bg=COLORS["surface"],
                 fg=COLORS["text"], borderwidth=0, relief="flat", insertbackground=COLORS["accent"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(14, 4), fill="x", expand=True)

        t_frame = tk.Frame(filter_container, bg=COLORS["surface"], padx=12, pady=8,
                           highlightthickness=1, highlightbackground=COLORS["border"])
        t_frame.pack(side=tk.LEFT, expand=True, fill="x", padx=(6, 0))
        tk.Label(t_frame, text="TEST", fg=COLORS["muted"], bg=COLORS["surface"],
                 font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)
        self.search_test = tk.StringVar()
        self.search_test.trace_add("write", self.filter_data)
        tk.Entry(t_frame, textvariable=self.search_test, bg=COLORS["surface"],
                 fg=COLORS["text"], borderwidth=0, relief="flat", insertbackground=COLORS["accent"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(14, 4), fill="x", expand=True)

    def _build_table(self):
        table_frame = tk.Frame(self.root, bg=COLORS["surface"], padx=1, pady=1,
                               highlightthickness=1, highlightbackground=COLORS["border"])
        table_frame.pack(expand=True, fill="both", padx=30, pady=(0, 12))
        cols = ('Test Name', 'Result')
        self.tree = ttk.Treeview(table_frame, columns=cols, show='tree headings', selectmode="extended")
        self.tree.heading('#0', text="PATIENT", anchor="w")
        self.tree.heading('Test Name', text="TEST TYPE", anchor="w")
        self.tree.heading('Result', text="RESULT", anchor="w")
        self.tree.column('#0', width=400, minwidth=220)
        self.tree.column('Test Name', width=300, minwidth=180)
        self.tree.column('Result', width=180, minwidth=120)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", expand=True, fill="both", padx=(8, 0), pady=6)
        scrollbar.pack(side="right", fill="y", pady=6, padx=(0, 4))
        self.tree.bind("<Button-3>", self._show_context_menu)

    def _build_context_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0, bg=COLORS["surface"], fg=COLORS["text"],
                            activebackground=COLORS["accent_soft"], activeforeground=COLORS["text"])
        self.menu.add_command(label="Delete selected patient", command=self.delete_individual)

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.menu.post(event.x_root, event.y_root)

    def _build_buttons(self):
        btn_frame = tk.Frame(self.root, bg=COLORS["background"])
        btn_frame.pack(fill="x", padx=30, pady=(0, 12))
        tk.Button(btn_frame, text="Save report and clear", bg=COLORS["accent"],
                  fg=COLORS["surface"], activebackground=COLORS["accent_hover"],
                  activeforeground=COLORS["surface"], font=("Segoe UI", 9, "bold"),
                  relief="flat", bd=0, command=self.save_to_csv, padx=18, pady=9,
                  cursor="hand2").pack(side="right")

    def _build_activity_log(self):
        activity_frame = tk.Frame(self.root, bg=COLORS["background"])
        activity_frame.pack(fill="x", padx=30, pady=(0, 18))
        tk.Label(activity_frame, text="FILE ACTIVITY", fg=COLORS["muted"],
                 bg=COLORS["background"], font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 5))
        log_content = tk.Frame(activity_frame, bg=COLORS["surface"],
                               highlightthickness=1, highlightbackground=COLORS["border"])
        log_content.pack(fill="x")
        self.activity_text = tk.Text(log_content, height=4, bg=COLORS["surface"],
                                     fg=COLORS["muted"], insertbackground=COLORS["accent"],
                                     relief="flat", wrap="word", padx=10, pady=8,
                                     font=("Consolas", 9), state="disabled")
        scrollbar = ttk.Scrollbar(log_content, orient="vertical", command=self.activity_text.yview)
        self.activity_text.configure(yscrollcommand=scrollbar.set)
        self.activity_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _flush_activity_log(self):
        messages = []
        while True:
            try:
                messages.append(self.activity_queue.get_nowait())
            except queue.Empty:
                break

        if messages:
            self.activity_text.config(state="normal")
            self.activity_text.insert("end", "".join(messages))
            self.activity_text.see("end")
            self.activity_text.config(state="disabled")

        self.root.after(100, self._flush_activity_log)

    def queue_activity_text(self, text):
        self.activity_queue.put(text)

    def filter_data(self, *args):
        for i in self.tree.get_children(): self.tree.delete(i)
        p_query = self.search_pat.get().lower()
        t_query = self.search_test.get().lower()
        
        grouped = {}
        for patient_id, name, test, res in self.all_records:
            if p_query in name.lower() and t_query in test.lower():
                if name not in grouped: grouped[name] = []
                grouped[name].append((test, res))
        
        for patient_name, tests in grouped.items():
            # 🕒 FEATURE: Time added to Patient Row
            entry_time = time.strftime("%H:%M:%S")
            parent = self.tree.insert("", "end", text=f"[{entry_time}]  {patient_name}", open=False)
            
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
        self.alert_text.config(text=text, fg=COLORS["offline"])
        self.root.after(10000, lambda: self.alert_text.config(text=""))

    def _show_alert(self, patient_id, patient_name, test_name, result, alert_reason):
        full_title = f"{alert_reason}: {test_name}"
        # Play alert sound and update status, but do NOT show in left notifications
        winsound.PlaySound("SystemHand", winsound.SND_ALIAS | winsound.SND_ASYNC)
        self._update_alert_status(
            f"{patient_id} | {patient_name} | {test_name} → {alert_reason}"
        )

    def _check_record_alert(self, patient_id, patient_name, test_name, result):
        alert_key = (patient_id, patient_name, test_name, result)
        if alert_key in self.alerted_records:
            return

        if result.strip().casefold() == "missing_result":
            self._show_alert(
                patient_id, patient_name, test_name, result, "MISSING_RESULT"
            )
            self.alerted_records.add(alert_key)
            return

        if self._is_technical_error(result):
            self._show_alert(
                patient_id, patient_name, test_name, result, "TECHNICAL ERROR"
            )
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
            self._show_alert(
                patient_id, patient_name, test_name, result, f"LOW (< {low})"
            )
            self.alerted_records.add(alert_key)
            return

        if high is not None and numeric > high:
            self._show_alert(
                patient_id, patient_name, test_name, result, f"HIGH (> {high})"
            )
            self.alerted_records.add(alert_key)
            return

    def update_network_status(self, online, path):
        """Update the network status indicator in the UI."""
        if online:
            self.status_dot.config(fg=COLORS["online"])
            self.status_text.config(text="ONLINE", fg=COLORS["online"])
        else:
            self.status_dot.config(fg=COLORS["offline"])
            self.status_text.config(text="OFFLINE", fg=COLORS["offline"])

    def delete_individual(self):
        selected = self.tree.selection()
        if not selected: return
        # Logic to extract name even with the timestamp prefix
        item_text = self.tree.item(selected[0])['text']
        raw_name = item_text.split("] ", 1)[-1].strip()
        # Remove from both records and notification tracking
        self.all_records = [r for r in self.all_records if r[1] != raw_name]
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
