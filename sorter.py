import os
import time
import csv
import tkinter as tk
from tkinter import ttk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- 1. SETUP ---
WATCH_FOLDER = r'C:\Users\user\Desktop\automate\LogFiles'
REPORT_PATH = r'C:\Users\user\Desktop\Patient_Report.csv' # Saves to Desktop

# --- 2. TEST MAPPING ---
TEST_MAP = {
    "768": "TOTAL BILIRUBIN", "220": "CONJUGATED (Direct)", "798": "UNCONJUGATED (Indirect)",
    "320": "AST / SGOT", "357": "ALT / SGPT", "321": "ALKALINE PHOSPHATASE",
    "366": "GGT", "774": "TOTAL PROTEIN", "672": "ALBUMIN",
    "137": "UREA",  "680": "SERUM CREATININE",
    "688": "URIC ACID", "701": "SODIUM (Na+)", "609": "POTASSIUM (K+)",
    "543": "uCRP", "544": "hsCRP", "301": "GLUCOSE",
    "539": "HbA1c", "928": "DERIVED HbA1c", "450": "LDH","300":"glucose","950": "hemolysis" , "951": "ict" ,"952":"turbidity" ,"539":"a1c" ,"927":"a1c"
}

class ProfessionalPopup:
    def __init__(self, filename, records):
        self.root = tk.Tk()
        self.root.title("🧬 New Patient Records Detected")
        self.root.geometry("600x400")
        self.root.attributes("-topmost", True) # Force to stay on top
        
        # Style
        style = ttk.Style()
        style.configure("Treeview", font=('Segoe UI', 10), rowheight=25)
        style.configure("Treeview.Heading", font=('Segoe UI', 11, 'bold'))

        # Header Label
        lbl = tk.Label(self.root, text=f"File: {filename}", font=("Segoe UI", 10, "italic"), fg="gray")
        lbl.pack(pady=5)

        # Table (Treeview)
        cols = ('Patient Name', 'Test Name', 'Result')
        self.tree = ttk.Treeview(self.root, columns=cols, show='headings')
        
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=180)
        
        for rec in records:
            self.tree.insert("", "end", values=rec)
        
        self.tree.pack(expand=True, fill='both', padx=10, pady=10)

        # Confirm Button
        btn = tk.Button(self.root, text="✅ CONFIRM & SAVE TO REPORT", bg="#2ecc71", fg="white", 
                         font=("Segoe UI", 11, "bold"), command=self.close_and_save)
        btn.pack(pady=15, ipadx=20)
        
        self.records_to_save = records
        self.root.mainloop()

    def close_and_save(self):
        # Save to CSV
        file_exists = os.path.isfile(REPORT_PATH)
        with open(REPORT_PATH, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Date/Time', 'Patient Name', 'Test Name', 'Result'])
            
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            for r in self.records_to_save:
                writer.writerow([timestamp, r[0], r[1], r[2]])
        
        self.root.destroy()

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
                        
                        if any(char.isalpha() for char in name) and "No Result" not in res:
                            test_name = TEST_MAP.get(tid, f"ID:{tid}")
                            valid_rows.append((name, test_name, res))

            if valid_rows:
                ProfessionalPopup(os.path.basename(event.src_path), valid_rows)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    if not os.path.exists(WATCH_FOLDER): os.makedirs(WATCH_FOLDER)
    print(f"🚀 System Online. Watching: {WATCH_FOLDER}")
    observer = Observer()
    observer.schedule(MedicalHandler(), WATCH_FOLDER, recursive=False)
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
