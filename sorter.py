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
import subprocess

# --- 1. SETUP ---
NETWORK_SOURCE = r'\\192.168.1.103\log1' 
WATCH_FOLDER = r'C:\Users\user\Desktop\automate\LogFiles'
REPORT_PATH = r'C:\Users\user\Desktop\Patient_Report.csv'

# --- 2. TEST MAPPING ---
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
        print("[CHECKPOINT 1] Initializing Modern GUI...")
        self.root = tk.Tk()
        self.root.title("🧬 Lab Monitor Pro")
        self.root.geometry("850x700")
        self.root.configure(bg="#f4f7f6")
        self.root.attributes("-topmost", True)
        
        self.all_records = []

        # --- TOP HEADER ---
        header = tk.Frame(self.root, bg="#2c3e50", height=60)
        header.pack(fill='x')
        tk.Label(header, text="LAB AUTOMATION SYSTEM", fg="white", bg="#2c3e50", 
                 font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT, padx=20, pady=15)

        # --- NETWORK STATUS BAR ---
        self.status_frame = tk.Frame(self.root, bg="#ffffff", bd=1, relief="groove")
        self.status_frame.pack(fill='x', padx=15, pady=10)
        
        self.status_dot = tk.Label(self.status_frame, text="●", fg="gray", font=("Arial", 14), bg="white")
        self.status_dot.pack(side=tk.LEFT, padx=(10, 0))
        
        self.status_text = tk.Label(self.status_frame, text="Checking Network...", font=("Segoe UI", 9, "bold"), bg="white")
        self.status_text.pack(side=tk.LEFT, padx=5)

        # --- MULTI-FILTER SECTION ---
        filter_container = tk.LabelFrame(self.root, text=" 🔍 Quick Filters ", font=("Segoe UI", 9, "bold"), bg="#f4f7f6", padx=10, pady=10)
        filter_container.pack(fill='x', padx=15, pady=5)

        # Patient Filter
        f_pat = tk.Frame(filter_container, bg="#f4f7f6")
        f_pat.pack(side=tk.LEFT, expand=True, fill='x')
        tk.Label(f_pat, text="Patient Name:", font=("Segoe UI", 8), bg="#f4f7f6").pack(anchor='w')
        self.search_pat = tk.StringVar()
        self.search_pat.trace_add("write", self.filter_data)
        tk.Entry(f_pat, textvariable=self.search_pat, font=("Segoe UI", 10)).pack(fill='x', padx=(0, 10))

        # Test Filter
        f_test = tk.Frame(filter_container, bg="#f4f7f6")
        f_test.pack(side=tk.LEFT, expand=True, fill='x')
        tk.Label(f_test, text="Test Type:", font=("Segoe UI", 8), bg="#f4f7f6").pack(anchor='w')
        self.search_test = tk.StringVar()
        self.search_test.trace_add("write", self.filter_data)
        tk.Entry(f_test, textvariable=self.search_test, font=("Segoe UI", 10)).pack(fill='x')

        # --- TABLE STYLING ---
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", rowheight=30, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#ecf0f1")

        cols = ('Patient Name', 'Test Name', 'Result')
        self.tree = ttk.Treeview(self.root, columns=cols, show='headings', selectmode="extended")
        
        self.tree.heading('Patient Name', text='PATIENT NAME')
        self.tree.column('Patient Name', width=350, anchor='w')
        
        self.tree.heading('Test Name', text='TEST TYPE')
        self.tree.column('Test Name', width=250, anchor='center')
        
        self.tree.heading('Result', text='RESULT')
        self.tree.column('Result', width=120, anchor='center')
        
        self.tree.pack(expand=True, fill='both', padx=15, pady=5)

        # Count Label
        self.count_label = tk.Label(self.root, text="Visible Records: 0", font=("Segoe UI", 8, "italic"), bg="#f4f7f6")
        self.count_label.pack(anchor='e', padx=15)

        # --- BUTTONS ---
        btn_frame = tk.Frame(self.root, bg="#f4f7f6")
        btn_frame.pack(pady=15)

        tk.Button(btn_frame, text=" 🗑 DELETE SELECTED ", bg="#e74c3c", fg="white", relief="flat",
                  font=("Segoe UI", 10, "bold"), command=self.delete_row, padx=20).pack(side=tk.LEFT, padx=10)
        
        tk.Button(btn_frame, text=" 💾 SAVE ALL & CLEAR ", bg="#2ecc71", fg="white", relief="flat",
                  font=("Segoe UI", 10, "bold"), command=self.save_to_csv, padx=20).pack(side=tk.LEFT, padx=10)

    def update_status(self, online=True):
        if online:
            self.status_dot.config(fg="#2ecc71")
            self.status_text.config(text=f"CONNECTED: {NETWORK_SOURCE}", fg="#27ae60")
        else:
            self.status_dot.config(fg="#e74c3c")
            self.status_text.config(text="OFFLINE - CHECK NETWORK", fg="#c0392b")

    def add_records(self, records):
        for rec in records:
            self.all_records.append(rec)
        self.filter_data() # Refresh view
        self.root.bell()

    def filter_data(self, *args):
        p_query = self.search_pat.get().lower()
        t_query = self.search_test.get().lower()
        
        filtered = [
            r for r in self.all_records 
            if p_query in str(r[0]).lower() and t_query in str(r[1]).lower()
        ]
        self.refresh_tree(filtered)

    def refresh_tree(self, data_list):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for rec in data_list:
            self.tree.insert("", "end", values=rec)
        self.count_label.config(text=f"Visible Records: {len(data_list)}")

    def delete_row(self):
        selected = self.tree.selection()
        if not selected: return
        
        if messagebox.askyesno("Confirm", "Delete selected rows?"):
            for item in selected:
                values = self.tree.item(item)['values']
                # Correct comparison for data types (Treeview converts everything to string)
                self.all_records = [r for r in self.all_records if [str(x) for x in r] != [str(x) for x in values]]
                self.tree.delete(item)
            self.count_label.config(text=f"Visible Records: {len(self.tree.get_children())}")

    def save_to_csv(self):
        if not self.all_records: return
        
        try:
            file_exists = os.path.isfile(REPORT_PATH)
            with open(REPORT_PATH, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['Date/Time', 'Patient Name', 'Test Name', 'Result'])
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                for rec in self.all_records:
                    writer.writerow([ts] + list(rec))
            
            self.all_records = []
            self.search_pat.set("")
            self.search_test.set("")
            self.refresh_tree([])
            messagebox.showinfo("Success", "Data saved successfully!")
        except PermissionError:
            messagebox.showerror("Error", "Close 'Patient_Report.csv' before saving!")

    def run(self):
        self.root.mainloop()

ui = None

class MedicalHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory: return
        time.sleep(1.5) 
        try:
            valid_rows = []
            with open(event.src_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parts = [p.strip() for p in line.split('\t')]
                    if len(parts) >= 6:
                        name, tid, res = parts[1], parts[4], parts[5]
                        if any(c.isalpha() for c in name) and "No Result" not in res:
                            test_display_name = TEST_MAP.get(tid, f"ID: {tid}")
                            valid_rows.append((name, test_display_name, res))
            if valid_rows and ui:
                ui.root.after(0, ui.add_records, valid_rows)
        except Exception as e: 
            print(f"Error reading file: {e}")

def sync_task():
    while True:
        try:
            host_ip = "192.168.1.103"
            subprocess.run(f"ping -n 1 -w 1000 {host_ip}", stdout=subprocess.DEVNULL, shell=True)
            online = os.path.isdir(NETWORK_SOURCE)
            if ui: ui.root.after(0, ui.update_status, online)
                
            if online:
                today_str = datetime.datetime.now().strftime("%m%d%Y")
                for f in os.listdir(NETWORK_SOURCE):
                    if f.startswith(today_str) and f.lower().endswith('r.log'):
                        src, dst = os.path.join(NETWORK_SOURCE, f), os.path.join(WATCH_FOLDER, f)
                        if os.path.isfile(src) and not os.path.exists(dst):
                            shutil.copy2(src, dst)
            else:
                print("Network disconnected. Waiting...")
        except Exception as e:
            print(f"Sync error: {e}")
        time.sleep(10)

if __name__ == "__main__":
    if not os.path.exists(WATCH_FOLDER): os.makedirs(WATCH_FOLDER)
    ui = SingletonPopup()
    threading.Thread(target=sync_task, daemon=True).start()
    observer = Observer()
    observer.schedule(MedicalHandler(), WATCH_FOLDER, recursive=False)
    observer.start()
    ui.run()
