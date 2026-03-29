import os
import time
import csv
import shutil
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

# --- 1. SETUP ---
NETWORK_SOURCE = r'\\YOUR_NETWORK_PC\SharedFolder' 
WATCH_FOLDER = r'C:\Users\user\Desktop\automate\LogFiles'
REPORT_PATH = r'C:\Users\user\Desktop\Patient_Report.csv'

TEST_MAP = {
    "768": "TOTAL BILIRUBIN", "220": "CONJUGATED (Direct)", "798": "UNCONJUGATED (Indirect)",
    "320": "AST / SGOT", "357": "ALT / SGPT", "321": "ALKALINE PHOSPHATASE",
    "366": "GGT", "774": "TOTAL PROTEIN", "672": "ALBUMIN",
    "137": "UREA",  "680": "SERUM CREATININE",
    "688": "URIC ACID", "701": "SODIUM (Na+)", "609": "POTASSIUM (K+)",
    "543": "uCRP", "544": "hsCRP", "301": "GLUCOSE",
    "539": "HbA1c", "928": "DERIVED HbA1c", "450": "LDH", "300": "glucose",
    "927": "a1c"
}

class SingletonPopup:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🧬 Lab Monitor Pro")
        self.root.geometry("750x550")
        self.root.attributes("-topmost", True)
        
        # --- Network Status Header ---
        self.status_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.status_frame.pack(fill='x', padx=10, pady=5)
        
        self.status_dot = tk.Label(self.status_frame, text="●", fg="gray", font=("Arial", 14))
        self.status_dot.pack(side=tk.LEFT)
        
        self.status_text = tk.Label(self.status_frame, text="Checking Network...", font=("Segoe UI", 10, "bold"))
        self.status_text.pack(side=tk.LEFT, padx=5)

        # Table Setup
        cols = ('Patient Name', 'Test Name', 'Result')
        self.tree = ttk.Treeview(self.root, columns=cols, show='headings')
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=200)
        self.tree.pack(expand=True, fill='both', padx=10, pady=10)

        # Buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="❌ DELETE SELECTED", bg="#e74c3c", fg="white", 
                  font=("Segoe UI", 10, "bold"), command=self.delete_row).pack(side=tk.LEFT, padx=10)
        
        tk.Button(btn_frame, text="✅ SAVE & CLEAR", bg="#2ecc71", fg="white", 
                  font=("Segoe UI", 10, "bold"), command=self.save_to_csv).pack(side=tk.LEFT, padx=10)

    def update_status(self, online=True):
        """Changes the UI indicator color based on network availability"""
        if online:
            self.status_dot.config(fg="#2ecc71") # Green
            self.status_text.config(text=f"NETWORK ONLINE: {NETWORK_SOURCE}", fg="#27ae60")
        else:
            self.status_dot.config(fg="#e74c3c") # Red
            self.status_text.config(text="NETWORK OFFLINE - Check Connection", fg="#c0392b")

    def add_records(self, records):
        for rec in records:
            self.tree.insert("", "end", values=rec)
        self.root.bell()

    def delete_row(self):
        selected = self.tree.selection()
        if selected: self.tree.delete(selected)

    def save_to_csv(self):
        items = self.tree.get_children()
        if not items: return
        file_exists = os.path.isfile(REPORT_PATH)
        with open(REPORT_PATH, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Date/Time', 'Patient Name', 'Test Name', 'Result'])
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            for i in items:
                writer.writerow([ts] + list(self.tree.item(i)['values']))
        for i in items: self.tree.delete(i)
        messagebox.showinfo("Success", "Data Saved.")

    def run(self):
        self.root.mainloop()

ui = None

class MedicalHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory: return
        time.sleep(1)
        try:
            valid_rows = []
            with open(event.src_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parts = [p.strip() for p in line.split('\t')]
                    if len(parts) >= 6:
                        name, tid, res = parts[1], parts[4], parts[5] # Fixed indexing from original code
                        if tid in TEST_MAP and any(c.isalpha() for c in name) and "No Result" not in res:
                            valid_rows.append((name, TEST_MAP[tid], res))
            if valid_rows and ui:
                ui.root.after(0, ui.add_records, valid_rows)
        except: pass

def sync_task():
    """Syncs today's files and updates UI status indicator"""
    while True:
        is_online = os.path.exists(NETWORK_SOURCE)
        
        # Update the UI indicator via thread-safe method
        if ui:
            ui.root.after(0, ui.update_status, is_online)
            
        if is_online:
            try:
                today_str = datetime.datetime.now().strftime("%m%d%Y")
                for f in os.listdir(NETWORK_SOURCE):
                    if f.startswith(today_str):
                        src, dst = os.path.join(NETWORK_SOURCE, f), os.path.join(WATCH_FOLDER, f)
                        if os.path.isfile(src) and not os.path.exists(dst):
                            shutil.copy2(src, dst)
            except: pass
        
        time.sleep(10) # Status updates every 10 seconds

if __name__ == "__main__":
    if not os.path.exists(WATCH_FOLDER): os.makedirs(WATCH_FOLDER)
    ui = SingletonPopup()
    threading.Thread(target=sync_task, daemon=True).start()
    
    observer = Observer()
    observer.schedule(MedicalHandler(), WATCH_FOLDER, recursive=False)
    observer.start()
    
    ui.run()
