import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

class HardwareTrackerWindow:
    def __init__(self, root, auth_controller, hardware_controller, logout_callback):
        self.root = root
        self.auth_controller = auth_controller
        self.hardware_controller = hardware_controller
        self.logout_callback = logout_callback
        self.selected_item_ids = set()

        for widget in self.root.winfo_children():
            widget.destroy()

        self.root.title("Campus Hardware Asset Tracker — Dashboard")
        self.root.geometry("1150x720")

        self.build_ui()

    def build_ui(self):
        main_container = ttk.Frame(self.root, style="TFrame")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Header Frame
        header_frame = ttk.Frame(main_container, style="Card.TFrame")
        header_frame.pack(fill="x", pady=(0, 15), ipady=10, ipadx=10)

        title_label = ttk.Label(header_frame, text="Hardware Asset Tracker Dashboard", style="Header.TLabel")
        title_label.pack(side="left", padx=10)

        user_info = getattr(self.auth_controller, 'current_user', {}) or {}
        username = user_info.get('username', 'User')
        role = user_info.get('role', 'STUDENT')

        user_label = ttk.Label(header_frame, text=f"Logged in as: {username} ({role})", style="Subheader.TLabel")
        user_label.pack(side="left", padx=20)

        logout_btn = ttk.Button(header_frame, text="Logout", style="Primary.TButton", command=self.logout)
        logout_btn.pack(side="right", padx=10)

        # Control Bar
        control_frame = ttk.Frame(main_container, style="Card.TFrame")
        control_frame.pack(fill="x", pady=(0, 15), ipady=10, ipadx=10)

        ttk.Label(control_frame, text="Search:", style="Card.TLabel").pack(side="left", padx=(10, 2))
        self.search_entry = ttk.Entry(control_frame, width=18)
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_table())

        ttk.Button(control_frame, text="Calculate Total Asset Value", style="Primary.TButton", command=self.show_total_value).pack(side="left", padx=4)
        ttk.Button(control_frame, text="Borrow Selected", style="Primary.TButton", command=self.borrow_selected_item).pack(side="left", padx=4)
        ttk.Button(control_frame, text="Delete Selected", style="Primary.TButton", command=self.delete_selected_item).pack(side="left", padx=4)
        ttk.Button(control_frame, text="Export CSV", style="Primary.TButton", command=self.export_csv).pack(side="left", padx=4)
        ttk.Button(control_frame, text="Refresh Table", style="Primary.TButton", command=self.refresh_table).pack(side="left", padx=4)

        # Table Frame
        table_frame = ttk.Frame(main_container, style="Card.TFrame")
        table_frame.pack(fill="both", expand=True, pady=(0, 15))

        columns = ("select", "id", "item_name", "category", "total_qty", "available_qty", "unit_price", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("select", text="[ Select ]")
        self.tree.heading("id", text="ID")
        self.tree.heading("item_name", text="Item Name")
        self.tree.heading("category", text="Category")
        self.tree.heading("total_qty", text="Total Qty")
        self.tree.heading("available_qty", text="Available Qty")
        self.tree.heading("unit_price", text="Unit Price ($)")
        self.tree.heading("status", text="Status")

        self.tree.column("select", width=70, anchor="center")
        self.tree.column("id", width=50, anchor="center")
        self.tree.column("item_name", width=200, anchor="w")
        self.tree.column("category", width=120, anchor="center")
        self.tree.column("total_qty", width=90, anchor="center")
        self.tree.column("available_qty", width=90, anchor="center")
        self.tree.column("unit_price", width=100, anchor="e")
        self.tree.column("status", width=110, anchor="center")

        # Color-coded Tag Configurations
        self.tree.tag_configure("in_stock", background="#1E3A2B", foreground="#A3E635")
        self.tree.tag_configure("low_stock", background="#3D2B1F", foreground="#FACC15")
        self.tree.tag_configure("out_of_stock", background="#3D1F24", foreground="#F87171")

        self.tree.bind("<Button-1>", self.on_table_click)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)

        # Add Item Form
        form_frame = ttk.Frame(main_container, style="Card.TFrame")
        form_frame.pack(fill="x", ipady=10, ipadx=10)

        ttk.Label(form_frame, text="Add New Item:", style="Card.TLabel").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        ttk.Label(form_frame, text="Name:", style="Card.TLabel").grid(row=0, column=1, padx=2)
        self.name_entry = ttk.Entry(form_frame, width=15)
        self.name_entry.grid(row=0, column=2, padx=5)

        ttk.Label(form_frame, text="Category:", style="Card.TLabel").grid(row=0, column=3, padx=2)
        self.cat_entry = ttk.Entry(form_frame, width=12)
        self.cat_entry.grid(row=0, column=4, padx=5)

        ttk.Label(form_frame, text="Qty:", style="Card.TLabel").grid(row=0, column=5, padx=2)
        self.qty_entry = ttk.Entry(form_frame, width=8)
        self.qty_entry.grid(row=0, column=6, padx=5)

        ttk.Label(form_frame, text="Price:", style="Card.TLabel").grid(row=0, column=7, padx=2)
        self.price_entry = ttk.Entry(form_frame, width=8)
        self.price_entry.grid(row=0, column=8, padx=5)

        ttk.Button(form_frame, text="Add Item", style="Primary.TButton", command=self.add_item).grid(row=0, column=9, padx=10)

        self.refresh_table()

    def refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        query = self.search_entry.get().strip() if hasattr(self, 'search_entry') else ""
        items = self.hardware_controller.fetch_all_items(search_query=query)

        for row in items:
            item_id = row[0]
            status = row[6]

            # Determine Checkbox state
            checkbox_str = "[✓]" if item_id in self.selected_item_ids else "[  ]"

            # Map Status to Tag
            if status == "In Stock":
                tag = "in_stock"
            elif status == "Low Stock":
                tag = "low_stock"
            else:
                tag = "out_of_stock"

            self.tree.insert("", "end", values=(checkbox_str, *row), tags=(tag,))

    def on_table_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            item_id_tree = self.tree.identify_row(event.y)
            if item_id_tree:
                values = self.tree.item(item_id_tree, "values")
                record_id = values[1]

                # Toggle Checkbox if clicking the Select column or row
                if column == "#1" or event.type == "4":
                    if record_id in self.selected_item_ids:
                        self.selected_item_ids.remove(record_id)
                    else:
                        self.selected_item_ids.add(record_id)
                    self.refresh_table()

    def show_total_value(self):
        total = self.hardware_controller.get_total_asset_value()
        messagebox.showinfo("Asset Valuation", f"Total Inventory Valuation: ${total:,.2f}")

    def borrow_selected_item(self):
        if not self.selected_item_ids:
            messagebox.showwarning("Selection Required", "Please check the box [✓] for an item to borrow.")
            return

        if len(self.selected_item_ids) > 1:
            messagebox.showwarning("Single Selection Needed", "Please select only one item at a time to borrow.")
            return

        item_id = list(self.selected_item_ids)[0]
        
        # Get Item Name
        items = self.hardware_controller.fetch_all_items()
        item_name = next((x[1] for x in items if x[0] == item_id), f"Item #{item_id}")

        qty_str = simpledialog.askstring("Borrow Equipment", f"How many '{item_name}' units do you want to borrow?", initialvalue="1")
        if not qty_str:
            return

        try:
            borrow_qty = int(qty_str)
            if borrow_qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Borrow quantity must be a positive integer.")
            return

        user_info = getattr(self.auth_controller, 'current_user', {}) or {}
        username = user_info.get('username', 'Student')

        success, msg = self.hardware_controller.borrow_item(username, item_id, borrow_qty)
        if success:
            messagebox.showinfo("Borrow Success", msg)
            self.selected_item_ids.clear()
            self.refresh_table()
        else:
            messagebox.showerror("Borrow Failed", msg)

    def delete_selected_item(self):
        if not self.selected_item_ids:
            messagebox.showwarning("Selection Required", "Please check the box [✓] for item(s) to delete.")
            return

        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete {len(self.selected_item_ids)} selected item(s)?")
        if confirm:
            for item_id in list(self.selected_item_ids):
                self.hardware_controller.delete_hardware_item(item_id)
            messagebox.showinfo("Deleted", "Selected item(s) deleted successfully!")
            self.selected_item_ids.clear()
            self.refresh_table()

    def export_csv(self):
        success, msg = self.hardware_controller.export_to_csv()
        if success:
            messagebox.showinfo("Export CSV", msg)
        else:
            messagebox.showerror("Export Failed", msg)

    def add_item(self):
        name = self.name_entry.get().strip()
        cat = self.cat_entry.get().strip()
        qty = self.qty_entry.get().strip()
        price = self.price_entry.get().strip()

        success, msg = self.hardware_controller.add_hardware_item(name, cat, qty, price)
        if success:
            messagebox.showinfo("Success", msg)
            self.name_entry.delete(0, tk.END)
            self.cat_entry.delete(0, tk.END)
            self.qty_entry.delete(0, tk.END)
            self.price_entry.delete(0, tk.END)
            self.refresh_table()
        else:
            messagebox.showerror("Blocked / Error", msg)

    def logout(self):
        self.logout_callback()