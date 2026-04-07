# Save this as interface.py
import tkinter as tk
from tkinter import ttk, messagebox
import csv, os, time
from config import REPORT_PATH # Gets the save path from config

class LabMonitorUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🧬 Lab Monitor Pro")
        self.root.geometry("850x700")
        self.root.configure(bg="#f4f7f6")
        self.root.attributes("-topmost", True)
        
        self.all_records = []
        self._build_header()
        self._build_status_bar()
        self._build_filters()
        self._build_table()
        self._build_buttons()

    def _build_header(self):
        header = tk.Frame(self.root, bg="#2c3e50", height=60)
        header.pack(fill='x')
        tk.Label(header, text="SHAHADATT", fg="white", bg="#2c3e50", 
                 font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT, padx=20, pady=15)

    def _build_status_bar(self):
        self.status_frame = tk.Frame(self.root, bg="#ffffff", bd=1, relief="groove")
        self.status_frame.pack(fill='x', padx=15, pady=10)
        self.status_dot = tk.Label(self.status_frame, text="●", fg="gray", font=("Arial", 14), bg="white")
        self.status_dot.pack(side=tk.LEFT, padx=(10, 0))
        self.status_text = tk.Label(self.status_frame, text="Checking...", bg="white")
        self.status_text.pack(side=tk.LEFT, padx=5)

    def _build_filters(self):
        f_cont = tk.LabelFrame(self.root, text=" 🔍 Filters ", bg="#f4f7f6")
        f_cont.pack(fill='x', padx=15, pady=5)
        
        self.search_pat = tk.StringVar()
        self.search_pat.trace_add("write", self.filter_data)
        tk.Entry(f_cont, textvariable=self.search_pat).pack(side=tk.LEFT, padx=10, pady=5, expand=True, fill='x')

    def _build_table(self):
        cols = ('Patient Name', 'Test Name', 'Result')
        self.tree = ttk.Treeview(self.root, columns=cols, show='headings')
        for col in cols: self.tree.heading(col, text=col.upper())
        self.tree.pack(expand=True, fill='both', padx=15)

    def _build_buttons(self):
        btn_frame = tk.Frame(self.root, bg="#f4f7f6")
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="SAVE & CLEAR", bg="#2ecc71", command=self.save_to_csv).pack()

    def update_status(self, online, msg):
        color = "#2ecc71" if online else "#e74c3c"
        self.status_dot.config(fg=color)
        self.status_text.config(text=msg)

    def add_records(self, records):
        self.all_records.extend(records)
        self.filter_data()
        self.root.bell()

    def filter_data(self, *args):
        query = self.search_pat.get().lower()
        self.tree.delete(*self.tree.get_children())
        for r in self.all_records:
            if query in str(r[0]).lower():
                self.tree.insert("", "end", values=r)

    def save_to_csv(self):
        if not self.all_records: return
        try:
            with open(REPORT_PATH, 'a', newline='') as f:
                writer = csv.writer(f)
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                for r in self.all_records: writer.writerow([ts] + list(r))
            self.all_records = []
            self.filter_data()
            messagebox.showinfo("Success", "Saved!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def run(self):
        self.root.mainloop()
