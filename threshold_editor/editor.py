import json
import tkinter as tk
from tkinter import ttk, messagebox
from config import save_critical_ranges, get_critical_ranges

class ThresholdEditor:
    def __init__(self, parent, app):
        self.app = app
        self.ranges = get_critical_ranges().copy()
        self.window = tk.Toplevel(parent)
        self.window.title("Threshold Editor")
        self.window.geometry("620x520")
        self.window.configure(bg="#0f172a")
        self.window.attributes("-topmost", True)

        self._build_ui()
        self._populate_fields()

    def _build_ui(self):
        header = tk.Frame(self.window, bg="#1e293b", pady=12)
        header.pack(fill="x")
        tk.Label(header, text="Critical Threshold Editor", fg="#38bdf8", bg="#1e293b",
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16)

        body = tk.Frame(self.window, bg="#0f172a")
        body.pack(fill="both", expand=True, padx=16, pady=12)

        cols = ("Test", "Low", "High")
        self.tree = ttk.Treeview(body, columns=cols, show="headings", height=18)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=170)
        self.tree.pack(fill="both", expand=True, side="left")

        self.tree.bind("<Double-1>", self._on_edit_cell)

        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        footer = tk.Frame(self.window, bg="#0f172a", pady=10)
        footer.pack(fill="x")
        tk.Button(footer, text="SAVE CHANGES", bg="#16a34a", fg="white", font=("Segoe UI", 10, "bold"),
                  relief="flat", command=self._save_changes, padx=16, pady=10, cursor="hand2").pack(side="right", padx=10)
        tk.Button(footer, text="CLOSE", bg="#ef4444", fg="white", font=("Segoe UI", 10, "bold"),
                  relief="flat", command=self.window.destroy, padx=16, pady=10, cursor="hand2").pack(side="right")

    def _populate_fields(self):
        for key, value in self.ranges.items():
            self.tree.insert("", "end", values=(key, value.get("low", ""), value.get("high", "")))

    def _on_edit_cell(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        column = self.tree.identify_column(event.x)
        if column == "#1":
            return

        x, y, width, height = self.tree.bbox(item_id, column)
        value = self.tree.set(item_id, column)

        self.edit_box = tk.Entry(self.tree, borderwidth=0, justify="center")
        self.edit_box.insert(0, value)
        self.edit_box.place(x=x, y=y, width=width, height=height)
        self.edit_box.focus()
        self.edit_box.bind("<Return>", lambda e: self._save_edit(item_id, column))
        self.edit_box.bind("<FocusOut>", lambda e: self._save_edit(item_id, column))

    def _save_edit(self, item_id, column):
        if not hasattr(self, "edit_box"):
            return
        new_value = self.edit_box.get().strip()
        self.tree.set(item_id, column, new_value)
        self.edit_box.destroy()
        del self.edit_box

    def _save_changes(self):
        new_ranges = {}
        for item_id in self.tree.get_children():
            test_name, low, high = self.tree.item(item_id, "values")
            entry = {}
            if low != "":
                try:
                    entry["low"] = float(low)
                except ValueError:
                    messagebox.showerror("Invalid value", f"Low value for {test_name} is invalid.")
                    return
            if high != "":
                try:
                    entry["high"] = float(high)
                except ValueError:
                    messagebox.showerror("Invalid value", f"High value for {test_name} is invalid.")
                    return
            if entry:
                new_ranges[test_name] = entry

        save_critical_ranges(new_ranges)
        self.app.critical_ranges = new_ranges
        messagebox.showinfo("Saved", "Thresholds saved successfully.")
