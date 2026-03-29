import os
import time
import csv
import tkinter as tk
from tkinter import ttk, messagebox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

# --- 1. SETUP ---
WATCH_FOLDER = r'C:\Users\user\Desktop\automate\LogFiles'
REPORT_PATH = r'C:\Users\user\Desktop\Patient_Report.csv'

# --- 2. TEST MAPPING (Updated: Removed hemolysis, ict, turbidity) ---
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
        self.root.title("🧬 Live Patient Records Monitor")
        self.root.geometry("700x500")
        self.root.attributes("-topmost", True)
        
        style = ttk.Style()
        style.configure("Treeview", font=('Segoe UI', 10), rowheight=25)
        style.configure("Treeview.Heading", font=('Segoe UI', 11, 'bold'))

        # Table
        cols = ('Patient Name', 'Test Name', 'Result')
        self.tree = ttk.Treeview(self.root, columns=cols, show='headings')
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=200)
        self.tree.pack(expand=True, fill='both', padx=10, pady=10)

        # Buttons Frame
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        # Delete Button
        btn_del = tk.Button(btn_frame, text="❌ DELETE SELECTED ROW", bg="#e74c3c", fg="white", 
                            font=("Segoe UI", 10, "bold"), command=self.delete_row)
        btn_del.pack(side=tk.LEFT, padx=10)

        # Save Button
        btn_save = tk.Button(btn_frame, text="✅ SAVE ALL TO REPORT & CLEAR", bg="#2ecc71", fg="white", 
                             font=("Segoe UI", 10, "bold"), command=self.save_to_csv)
        btn_save.pack(side=tk.LEFT, padx=10)

    def add_records(self, records):
        """Adds new data to the bottom of the table without refreshing the window"""
        for rec in records:
            self.tree.insert("", "end", values=rec)
        self.root.bell() # Subtle beep when new data arrives

    def delete_row(self):
        selected_item = self.tree.selection()
        if selected_item:
            self.tree.delete(selected_item)
        else:
            messagebox.showwarning("Select Row", "Please click on a row first to delete it.")

    def save_to_csv(self):
        all_items = self.tree.get_children()
        if not all_items:
            messagebox.showinfo("Empty", "No records to save.")
            return

        file_exists = os.path.isfile(REPORT_PATH)
        with open(REPORT_PATH, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Date/Time', 'Patient Name', 'Test Name', 'Result'])
            
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            for item in all_items:
                row_values = self.tree.item(item)['values']
                writer.writerow([timestamp] + list(row_values))
        
        # Clear table after saving
        for item in all_items:
            self.tree.delete(item)
        messagebox.showinfo("Success", "Records saved to Patient_Report.csv")

    def run(self):
        self.root.mainloop()

# Global variable to hold our single window instance
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
                        
                        # Only add if the test ID is in our map (skips hemolysis, etc.)
                        if tid in TEST_MAP and any(char.isalpha() for char in name) and "No Result" not in res:
                            test_name = TEST_MAP[tid]
                            valid_rows.append((name, test_name, res))

            if valid_rows and ui:
                # Add data to the existing window using a thread-safe method
                ui.root.after(0, ui.add_records, valid_rows)
        except Exception as e:
            print(f"Error reading file: {e}")

def start_observer():
    observer = Observer()
    observer.schedule(MedicalHandler(), WATCH_FOLDER, recursive=False)
    observer.start()
    try:
        while True: time.sleep(1)
    except:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    if not os.path.exists(WATCH_FOLDER): os.makedirs(WATCH_FOLDER)
    print(f"🚀 System Online. Watching: {WATCH_FOLDER}")
    
    # Initialize the single UI window
    ui = SingletonPopup()
    
    # Start the folder watcher in a separate thread so it doesn't freeze the window
    threading.Thread(target=start_observer, daemon=True).start()
    
    # Run the window
    ui.run()
