import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import theme

class AdminDashboardWindow:
    def __init__(self, root, user, hardware_controller, logout_callback, auth_controller=None):
        self.root = root
        self.user = user
        self.hardware_controller = hardware_controller
        self.logout_callback = logout_callback
        self.auth_controller = auth_controller

        if isinstance(self.user, dict):
            self.admin_name = self.user.get("username", "Admin")
        else:
            self.admin_name = str(self.user)

        for widget in self.root.winfo_children():
            widget.destroy()

        self.setup_ui()
        
        # Subscribe observer pattern for same-process actions
        if hasattr(self.hardware_controller, "subscribe"):
            self.hardware_controller.subscribe(self.refresh_all_data)

        # Force initial data load
        self.refresh_all_data()

        # Start Real-Time Background Polling (Every 3,000 ms / 3 seconds)
        self.schedule_auto_refresh()

    def schedule_auto_refresh(self):
        """Polls the database continuously to reflect changes across processes."""
        if hasattr(self, 'root') and self.root.winfo_exists():
            self.refresh_all_data()
            # Schedule next update in 3000 ms
            self.root.after(3000, self.schedule_auto_refresh)

    def setup_ui(self):
        # Top navigation bar
        topbar = ttk.Frame(self.root, style="Topbar.TFrame")
        topbar.pack(fill="x")

        brand_frame = ttk.Frame(topbar, style="Topbar.TFrame")
        brand_frame.pack(side="left", padx=(20, 0), pady=12)
        ttk.Label(brand_frame, text="NU", style="BrandMark.TLabel").pack(side="left")
        ttk.Label(brand_frame, text="NU Hardware Inventory", style="BrandName.TLabel").pack(side="left", padx=(10, 0))

        actions = ttk.Frame(topbar, style="Topbar.TFrame")
        actions.pack(side="right", padx=20, pady=12)

        ttk.Button(actions, text="Dashboard", style="Nav.TButton", command=lambda: self.notebook.select(0)).pack(side="left", padx=(0, 8))
        ttk.Label(actions, text=f"{self.admin_name[:1].upper()}", style="WelcomeName.TLabel", width=2).pack(side="left")
        ttk.Label(actions, text=f"{self.admin_name}", style="BrandSub.TLabel").pack(side="left", padx=(6, 12))
        ttk.Button(actions, text="Logout", style="Nav.TButton", command=self.logout_callback).pack(side="left")

        success_banner = ttk.Label(self.root, text="✓ Login successful!", style="Success.TLabel", anchor="w")
        success_banner.pack(fill="x", padx=20, pady=(14, 0))

        title_row = ttk.Frame(self.root, style="Panel.TFrame")
        title_row.pack(fill="x", padx=20, pady=(18, 12))

        title_group = ttk.Frame(title_row, style="Panel.TFrame")
        title_group.pack(side="left", anchor="w")

        ttk.Label(title_group, text="Laboratory Dashboard", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_group, text=f"Good day, {self.admin_name}!", style="Welcome.TLabel").pack(anchor="w", pady=(4, 0))

        action_group = ttk.Frame(title_row, style="Panel.TFrame")
        action_group.pack(side="right")
        self.notification_button = ttk.Button(action_group, text="Notifications (0)", style="Primary.TButton", command=self.show_notifications)
        self.notification_button.pack(side="right", padx=(0, 8))
        ttk.Button(action_group, text="Export Inventory CSV", style="Primary.TButton", command=self.export_inventory_report).pack(side="right")

        self.metrics_frame = ttk.Frame(self.root, style="Panel.TFrame")
        self.metrics_frame.pack(fill="x", padx=20, pady=(0, 6))
        self.metric_labels = {}
        for key, label, color in (
            ("available_units", "Stock", "#4F8EF7"),
            ("low_stock_items", "Low stock", "#F4B41A"),
            ("pending_requests", "Pending", "#10B981"),
            ("overdue_requests", "Overdue", "#F06A75"),
            ("total_asset_value", "Asset", "#7C3AED"),
        ):
            metric = ttk.Frame(self.metrics_frame, style="Card.TFrame", padding=10)
            metric.pack(side="left", padx=(0, 10), fill="y")
            ttk.Label(metric, text="●", foreground=color, background=theme.CARD_BG, font=("Segoe UI", 11, "bold")).pack(side="left")
            value_label = ttk.Label(metric, text=f"0 {label}", style="MetricValue.TLabel", font=("Segoe UI", 11, "bold"))
            value_label.pack(side="left", padx=(6, 0))
            self.metric_labels[key] = (value_label, label)

        metrics_legend = ttk.Frame(self.root, style="Panel.TFrame")
        metrics_legend.pack(fill="x", padx=20, pady=(0, 10))
        ttk.Label(metrics_legend, text="Color legend:", style="CardLabel.TLabel", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 8))
        for label, color in (("Stock", "#4F8EF7"), ("Low stock", "#F4B41A"), ("Pending", "#10B981"), ("Overdue", "#F06A75")):
            item = ttk.Frame(metrics_legend, style="Panel.TFrame")
            item.pack(side="left", padx=(0, 10))
            ttk.Label(item, text="●", foreground=color, background=theme.BG_PAGE, font=("Segoe UI", 9, "bold")).pack(side="left")
            ttk.Label(item, text=label, background=theme.BG_PAGE, foreground=theme.TEXT_MUTED, font=("Segoe UI", 8, "bold")).pack(side="left", padx=(3, 0))

        # Notebook / Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # 1. Hardware Tab
        self.tab_hardware = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_hardware, text="Hardware Inventory")

        # 2. Student Requests Tab
        self.tab_requests = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_requests, text="Student Requests")

        # 3. Audit Log Tab
        self.tab_audit = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_audit, text="System Audit Log")

        self.tab_users = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_users, text="User Accounts")

        # Bind tab change event to refresh UI immediately on tab switch
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self.refresh_all_data())

        # --- HARDWARE TAB UI ---
        btn_bar = ttk.Frame(self.tab_hardware)
        btn_bar.pack(fill="x", padx=15, pady=10)

        ttk.Label(btn_bar, text="Search:", style="CardLabel.TLabel").pack(side="left", padx=(0, 6))
        self.hardware_search = tk.StringVar()
        search_entry = ttk.Entry(btn_bar, textvariable=self.hardware_search, width=24)
        search_entry.pack(side="left")
        search_entry.bind("<KeyRelease>", lambda event: self.load_hardware_data())
        ttk.Button(btn_bar, text="Clear", command=lambda: (self.hardware_search.set(""), self.load_hardware_data())).pack(side="left", padx=6)
        ttk.Button(btn_bar, text="Condition History", command=self.show_condition_history).pack(side="left", padx=6)

        add_btn = ttk.Button(
            btn_bar, 
            text="+ Add Item", 
            style="Primary.TButton",
            command=self.add_new_item
        )
        add_btn.pack(side="right", padx=5)

        edit_btn = ttk.Button(
            btn_bar,
            text="Edit Item",
            style="Primary.TButton",
            command=self.edit_selected
        )
        edit_btn.pack(side="right", padx=5)

        del_btn = ttk.Button(
            btn_bar, 
            text="Delete Selected", 
            style="Danger.TButton",
            command=self.delete_selected
        )
        del_btn.pack(side="right")

        columns = ("id", "name", "category", "stock_qty", "unit_price", "status", "condition", "select")
        self.tree = ttk.Treeview(self.tab_hardware, columns=columns, show="headings", selectmode="extended")

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Item Name")
        self.tree.heading("category", text="Category")
        self.tree.heading("stock_qty", text="Stock Qty")
        self.tree.heading("unit_price", text="Unit Price")
        self.tree.heading("status", text="Status")
        self.tree.heading("condition", text="Condition")
        self.tree.heading("select", text="Select")

        self.tree.column("id", width=80, anchor="center")
        self.tree.column("name", width=220, anchor="w")
        self.tree.column("category", width=140, anchor="w")
        self.tree.column("stock_qty", width=90, anchor="center")
        self.tree.column("unit_price", width=120, anchor="e")
        self.tree.column("status", width=110, anchor="center")
        self.tree.column("condition", width=110, anchor="center")
        self.tree.column("select", width=65, anchor="center", stretch=False)
        self.tree.bind("<Button-1>", self.toggle_checkbox)

        self.tree.tag_configure("in_stock", foreground="#22C55E")
        self.tree.tag_configure("low_stock", foreground="#FACC15")
        self.tree.tag_configure("out_of_stock", foreground="#EF4444")

        self.tree.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.add_legend(self.tab_hardware, "STOCK:", (("In stock", "#16803C"), ("Low stock", "#A56800"), ("Out of stock", theme.DANGER_RED)))

        # --- STUDENT REQUESTS TAB UI ---
        req_btn_bar = ttk.Frame(self.tab_requests)
        req_btn_bar.pack(fill="x", padx=15, pady=10)

        approve_btn = ttk.Button(
            req_btn_bar, 
            text="Approve Request", 
            style="Primary.TButton",
            command=self.approve_selected_request
        )
        approve_btn.pack(side="left", padx=(0, 5))

        decline_btn = ttk.Button(
            req_btn_bar, 
            text="Decline Request", 
            style="Danger.TButton",
            command=self.decline_selected_request
        )
        decline_btn.pack(side="left")

        return_btn = ttk.Button(
            req_btn_bar,
            text="Record Return",
            style="Primary.TButton",
            command=self.record_return
        )
        return_btn.pack(side="right")
        req_columns = ("id", "username", "hardware_id", "qty", "date", "due_date", "purpose", "instructor", "status", "approved_by", "select")
        request_table = ttk.Frame(self.tab_requests)
        request_table.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.req_tree = ttk.Treeview(request_table, columns=req_columns, show="headings", selectmode="extended")
        request_scrollbar = ttk.Scrollbar(request_table, orient="horizontal", command=self.req_tree.xview)
        self.req_tree.configure(xscrollcommand=request_scrollbar.set)
        self.req_tree.tag_configure("approved", foreground="#16803C")
        self.req_tree.tag_configure("declined", foreground=theme.DANGER_RED)
        self.req_tree.tag_configure("submitted", foreground="#A56800")
        self.req_tree.tag_configure("return_requested", foreground="#7C3AED")

        self.req_tree.heading("id", text="ID")
        self.req_tree.heading("username", text="Student")
        self.req_tree.heading("hardware_id", text="Hardware ID")
        self.req_tree.heading("qty", text="Qty")
        self.req_tree.heading("date", text="Borrow Date")
        self.req_tree.heading("due_date", text="Return Due")
        self.req_tree.heading("purpose", text="Purpose")
        self.req_tree.heading("instructor", text="Instructor")
        self.req_tree.heading("status", text="Status")
        self.req_tree.heading("approved_by", text="Handled By")
        self.req_tree.heading("select", text="Select")

        self.req_tree.column("id", width=40, anchor="center")
        self.req_tree.column("username", width=95, anchor="w", stretch=False)
        self.req_tree.column("hardware_id", width=80, anchor="center", stretch=False)
        self.req_tree.column("qty", width=45, anchor="center", stretch=False)
        self.req_tree.column("date", width=95, anchor="center", stretch=False)
        self.req_tree.column("due_date", width=90, anchor="center", stretch=False)
        self.req_tree.column("purpose", width=145, anchor="w", stretch=False)
        self.req_tree.column("instructor", width=110, anchor="w", stretch=False)
        self.req_tree.column("status", width=120, anchor="center", stretch=False)
        self.req_tree.column("approved_by", width=95, anchor="center", stretch=False)
        self.req_tree.column("select", width=65, anchor="center", stretch=False)
        self.req_tree.bind("<Button-1>", self.toggle_checkbox)

        self.req_tree.grid(row=0, column=0, sticky="nsew")
        request_scrollbar.grid(row=1, column=0, sticky="ew")
        request_table.rowconfigure(0, weight=1)
        request_table.columnconfigure(0, weight=1)

        legend = ttk.Frame(self.tab_requests, style="Portal.TFrame")
        legend.pack(fill="x", padx=15, pady=(0, 6))
        ttk.Label(legend, text="STATUS:", style="PortalHeading.TLabel").pack(side="left", padx=(8, 12))
        for label, color in (("Approved", "#16803C"), ("Declined", theme.DANGER_RED), ("Submitted", "#A56800"), ("Return requested", "#7C3AED")):
            item = tk.Frame(legend, bg="#EAF1F7")
            item.pack(side="left", padx=(0, 14))
            tk.Label(item, text="●", bg="#EAF1F7", fg=color, font=("Segoe UI", 14, "bold")).pack(side="left")
            tk.Label(item, text=label, bg="#EAF1F7", fg=theme.TEXT_MUTED, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(3, 0))

        # --- SYSTEM AUDIT LOG TAB UI ---
        audit_columns = ("id", "action", "details", "performed_by", "timestamp", "select")
        self.audit_tree = ttk.Treeview(self.tab_audit, columns=audit_columns, show="headings", selectmode="extended")
        self.audit_tree.tag_configure("approved", foreground="#16803C")
        self.audit_tree.tag_configure("declined", foreground=theme.DANGER_RED)
        self.audit_tree.tag_configure("submitted", foreground="#A56800")

        self.audit_tree.heading("id", text="Log ID")
        self.audit_tree.heading("action", text="Action")
        self.audit_tree.heading("details", text="Details")
        self.audit_tree.heading("performed_by", text="Performed By")
        self.audit_tree.heading("timestamp", text="Timestamp")
        self.audit_tree.heading("select", text="Select")

        self.audit_tree.column("id", width=50, anchor="center")
        self.audit_tree.column("action", width=140, anchor="center")
        self.audit_tree.column("details", width=320, anchor="w")
        self.audit_tree.column("performed_by", width=110, anchor="center")
        self.audit_tree.column("timestamp", width=150, anchor="center")
        self.audit_tree.column("select", width=65, anchor="center", stretch=False)
        self.audit_tree.bind("<Button-1>", self.toggle_checkbox)

        self.audit_tree.pack(fill="both", expand=True, padx=15, pady=15)
        self.add_legend(self.tab_audit, "ACTIONS:", (("Approved", "#16803C"), ("Declined", theme.DANGER_RED), ("Submitted", "#A56800"), ("Returned", "#7C3AED")))

        self.build_users_tab()

    def update_notifications_button(self):
        unread_count = len(self.hardware_controller.get_notifications())
        if hasattr(self, "notification_button") and self.notification_button.winfo_exists():
            self.notification_button.configure(text=f"Notifications ({unread_count})")

    def show_notifications(self):
        notifications = self.hardware_controller.get_all_notifications()
        if not notifications:
            notifications = [{"id": 0, "message": "There are no active alerts.", "read": True}]

        dialog = tk.Toplevel(self.root)
        dialog.title("Notifications")
        dialog.geometry("520x360")
        dialog.configure(bg=theme.BG_PAGE)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        outer = tk.Frame(dialog, bg=theme.BG_PAGE, padx=18, pady=18)
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg=theme.CARD_BG, padx=16, pady=12, highlightthickness=1, highlightbackground=theme.BORDER_COLOR)
        header.pack(fill="x")

        tk.Label(header, text="◔", bg=theme.CARD_BG, fg=theme.TEXT_LIGHT, font=("Segoe UI", 16, "bold")).pack(side="left")
        tk.Label(header, text="Notifications", bg=theme.CARD_BG, fg=theme.TEXT_LIGHT, font=("Segoe UI", 14, "bold")).pack(side="left", padx=(10, 0))

        tk.Button(
            header,
            text="✕",
            bg=theme.CARD_BG,
            fg=theme.TEXT_LIGHT,
            bd=0,
            highlightthickness=0,
            command=dialog.destroy,
            font=("Segoe UI", 12, "bold")
        ).pack(side="right")

        body = tk.Frame(outer, bg=theme.CARD_BG, padx=12, pady=12, highlightthickness=1, highlightbackground=theme.BORDER_COLOR)
        body.pack(fill="both", expand=True, pady=(14, 8))

        canvas = tk.Canvas(body, bg=theme.CARD_BG, highlightthickness=0, height=170)
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=theme.CARD_BG)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        for notification in notifications:
            row = tk.Frame(scroll_frame, bg=theme.CARD_BG, padx=8, pady=8, highlightthickness=1, highlightbackground=theme.BORDER_COLOR)
            row.pack(fill="x", pady=4)

            status = tk.Label(
                row,
                text="Unread" if not notification.get("read", True) else "Read",
                bg=theme.CARD_BG,
                fg=theme.ACCENT_BLUE if not notification.get("read", True) else "#6B7280",
                font=("Segoe UI", 9, "bold")
            )
            status.pack(anchor="w")

            tk.Label(
                row,
                text=notification.get("message", ""),
                bg=theme.CARD_BG,
                fg=theme.TEXT_LIGHT if not notification.get("read", True) else "#4B5563",
                font=("Segoe UI", 10),
                justify="left",
                wraplength=360,
                anchor="w"
            ).pack(anchor="w", pady=(4, 0), fill="x")

            if not notification.get("read", True):
                tk.Button(
                    row,
                    text="Mark as read",
                    bg=theme.ACCENT_BLUE,
                    fg="white",
                    bd=0,
                    highlightthickness=0,
                    padx=8,
                    pady=4,
                    command=lambda notification_id=notification.get("id", 0): (
                        self.hardware_controller.mark_notification_read(notification_id),
                        self.update_notifications_button(),
                        self.refresh_all_data(),
                        dialog.destroy()
                    )
                ).pack(anchor="e", pady=(6, 0))

        scroll_frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

        button_frame = tk.Frame(outer, bg=theme.BG_PAGE, pady=(8, 0))
        button_frame.pack(fill="x")
        tk.Button(
            button_frame,
            text="OK",
            bg=theme.ACCENT_BLUE,
            fg="white",
            bd=0,
            highlightthickness=0,
            padx=20,
            pady=8,
            font=("Segoe UI", 10, "bold"),
            command=dialog.destroy
        ).pack(anchor="center")

        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

    def backup_database(self):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Backup Inventory Database",
            defaultextension=".db",
            filetypes=(("SQLite database", "*.db"), ("All files", "*.*"))
        )
        if path and self.hardware_controller.backup_database(path):
            messagebox.showinfo("Backup Complete", "The inventory database was backed up successfully.", parent=self.root)

    def restore_database(self):
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Restore Inventory Database",
            filetypes=(("SQLite database", "*.db"), ("All files", "*.*"))
        )
        if not path:
            return
        if not messagebox.askyesno("Confirm Restore", "Restore this backup? Current inventory data will be replaced.", parent=self.root):
            return
        if self.hardware_controller.restore_database(path):
            self.refresh_all_data()
            messagebox.showinfo("Restore Complete", "The inventory database was restored successfully.", parent=self.root)
        else:
            messagebox.showerror("Restore Failed", "The selected file could not be restored.", parent=self.root)

    def show_condition_history(self):
        selected = self.tree.selection()
        if len(selected) != 1:
            messagebox.showwarning("Select One Item", "Select one hardware item first.", parent=self.root)
            return
        hardware_id = self.tree.item(selected[0], "values")[0]
        history = tk.Toplevel(self.root)
        history.title(f"Condition History - {hardware_id}")
        history.geometry("760x360")
        ttk.Label(history, text=f"Condition History: {hardware_id}", style="Header.TLabel").pack(anchor="w", padx=18, pady=14)
        columns = ("old", "new", "reason", "changed_by", "changed_at")
        tree = ttk.Treeview(history, columns=columns, show="headings")
        for column, heading, width in (("old", "Previous", 90), ("new", "New", 90), ("reason", "Reason", 260), ("changed_by", "Changed By", 110), ("changed_at", "Date", 150)):
            tree.heading(column, text=heading)
            tree.column(column, width=width, anchor="w")
        for row in self.hardware_controller.get_condition_history(hardware_id):
            tree.insert("", "end", values=(row["old_condition"], row["new_condition"], row["reason"], row["changed_by"], row["changed_at"]))
        tree.pack(fill="both", expand=True, padx=18, pady=(0, 18))

    def export_inventory_report(self):
        self.export_report("inventory")

    def export_report(self, report_type):
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".csv", filetypes=(("CSV files", "*.csv"),))
        if path and self.hardware_controller.export_report(report_type, path):
            messagebox.showinfo("Report Exported", f"Report saved to:\n{path}", parent=self.root)

    def build_users_tab(self):
        if not self.auth_controller:
            ttk.Label(self.tab_users, text="User management is unavailable.").pack(padx=15, pady=15)
            return
        toolbar = ttk.Frame(self.tab_users)
        toolbar.pack(fill="x", padx=15, pady=10)
        ttk.Button(toolbar, text="Change Role", style="Primary.TButton", command=self.change_user_role).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="Reset Password", style="Primary.TButton", command=self.reset_user_password).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="Delete User", style="Danger.TButton", command=self.delete_user).pack(side="left")
        self.user_tree = ttk.Treeview(self.tab_users, columns=("username", "email", "role"), show="headings")
        for column, heading, width in (("username", "Username", 180), ("email", "Email", 280), ("role", "Role", 120)):
            self.user_tree.heading(column, text=heading)
            self.user_tree.column(column, width=width, anchor="w")
        self.user_tree.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.load_users()

    def load_users(self):
        if hasattr(self, "user_tree"):
            self.user_tree.delete(*self.user_tree.get_children())
            for user in self.auth_controller.get_users():
                self.user_tree.insert("", "end", values=(user["username"], user["email"], user["role"]))

    def selected_username(self):
        selected = self.user_tree.selection()
        if not selected:
            messagebox.showwarning("Select User", "Select a user first.", parent=self.root)
            return None
        return self.user_tree.item(selected[0], "values")[0]

    def change_user_role(self):
        username = self.selected_username()
        if username and self.auth_controller.set_user_role(username, "ADMIN" if self.user_tree.item(self.user_tree.selection()[0], "values")[2] == "STUDENT" else "STUDENT"):
            self.load_users()

    def reset_user_password(self):
        username = self.selected_username()
        if username:
            password = simpledialog.askstring("Reset Password", "New password (8+ characters):", parent=self.root, show="*")
            if password and self.auth_controller.admin_reset_password(username, password):
                messagebox.showinfo("Password Reset", "Password updated successfully.", parent=self.root)
            else:
                messagebox.showerror("Password Reset", "Password must contain at least 8 characters.", parent=self.root)

    def delete_user(self):
        username = self.selected_username()
        if username and messagebox.askyesno("Delete User", f"Delete account '{username}'?", parent=self.root):
            if self.auth_controller.delete_user(username):
                self.load_users()

    def add_legend(self, parent, title, entries):
        legend = ttk.Frame(parent, style="Portal.TFrame")
        legend.pack(fill="x", padx=15, pady=(0, 6))
        ttk.Label(legend, text=title, style="PortalHeading.TLabel").pack(side="left", padx=(8, 12))
        for label, color in entries:
            item = tk.Frame(legend, bg="#EAF1F7")
            item.pack(side="left", padx=(0, 14))
            tk.Label(item, text="●", bg="#EAF1F7", fg=color, font=("Segoe UI", 14, "bold")).pack(side="left")
            tk.Label(item, text=label, bg="#EAF1F7", fg=theme.TEXT_MUTED, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(3, 0))

    def toggle_checkbox(self, event):
        tree = event.widget
        if tree.identify_column(event.x) != f"#{len(tree['columns'])}":
            return
        row = tree.identify_row(event.y)
        if not row:
            return "break"
        values = list(tree.item(row, "values"))
        is_selected = values[-1] == "[x]"
        values[-1] = "[ ]" if is_selected else "[x]"
        tree.item(row, values=values)
        if is_selected:
            tree.selection_remove(row)
        else:
            tree.selection_add(row)
        return "break"

    def refresh_all_data(self):
        if hasattr(self, "metrics_frame"):
            metrics = self.hardware_controller.get_dashboard_metrics()
            for key, (label, caption) in self.metric_labels.items():
                if key == "total_asset_value":
                    label.config(text=f"₱{metrics.get(key, 0):,.2f} {caption}")
                else:
                    label.config(text=f"{metrics[key]} {caption}")
        self.update_notifications_button()
        self.load_hardware_data()
        self.load_requests_data()
        self.load_audit_data()

    def load_hardware_data(self):
        if not hasattr(self, 'tree') or not self.tree.winfo_exists():
            return
        
        selected_ids = {
            self.tree.item(row, "values")[0]
            for row in self.tree.selection()
        }
        
        for item in self.tree.get_children():
            self.tree.delete(item)

        query = getattr(self, "hardware_search", tk.StringVar()).get()
        items = self.hardware_controller.search_hardware(query) if hasattr(self.hardware_controller, "search_hardware") else self.hardware_controller.get_all_hardware()
        for hw in items:
            status = hw.get("status", "OUT OF STOCK")
            status_tag = {
                "IN STOCK": "in_stock",
                "LOW STOCK": "low_stock",
                "OUT OF STOCK": "out_of_stock"
            }.get(status, "")
            self.tree.insert(
                "",
                "end",
                values=(
                    hw.get("id", ""),
                    hw.get("name", ""),
                    hw.get("category", ""),
                    hw.get("stock_qty", 0),
                    f"₱{float(hw.get('unit_price', 0) or 0):,.2f}",
                    status,
                    hw.get("condition", "GOOD"),
                    "[x]" if str(hw.get("id", "")) in selected_ids else "[ ]"
                ),
                tags=(status_tag,)
            )
        for row in self.tree.get_children():
            if str(self.tree.item(row, "values")[0]) in selected_ids:
                self.tree.selection_add(row)

    def load_requests_data(self):
        if not hasattr(self, 'req_tree') or not self.req_tree.winfo_exists():
            return

        selected_ids = {
            self.req_tree.item(row, "values")[0]
            for row in self.req_tree.selection()
        }
        for item in self.req_tree.get_children():
            self.req_tree.delete(item)

        if hasattr(self.hardware_controller, "get_all_requests"):
            requests = self.hardware_controller.get_all_requests()
            for req in requests:
                status = str(req.get("status", "")).upper()
                purpose = req.get("purpose")
                instructor = req.get("instructor")
                legacy_notes = req.get("return_due_date") or "-"
                if not purpose and not instructor and str(legacy_notes).startswith("Purpose:"):
                    purpose = legacy_notes.split(" | Instructor:", 1)[0].replace("Purpose:", "").strip()
                    instructor = legacy_notes.split(" | Instructor:", 1)[1].strip() if " | Instructor:" in legacy_notes else "-"
                status_tag = {
                    "APPROVED": "approved",
                    "DECLINED": "declined",
                    "SUBMITTED": "submitted",
                    "PENDING": "submitted",
                    "RETURN_REQUESTED": "return_requested"
                }.get(status, "")
                self.req_tree.insert(
                    "",
                    "end",
                    values=(
                        req.get("id"),
                        req.get("username"),
                        req.get("hardware_id"),
                        req.get("borrow_qty"),
                        req.get("borrow_date"),
                        req.get("return_due_date") if not str(legacy_notes).startswith("Purpose:") else "-",
                        purpose or "-",
                        instructor or "-",
                        status,
                        req.get("approved_by", "-"),
                        "[x]" if str(req.get("id")) in selected_ids else "[ ]"
                    ),
                    tags=(status_tag,)
                )
            for row in self.req_tree.get_children():
                if str(self.req_tree.item(row, "values")[0]) in selected_ids:
                    self.req_tree.selection_add(row)

    def load_audit_data(self):
        if not hasattr(self, 'audit_tree') or not self.audit_tree.winfo_exists():
            return

        # Fetch current items in tree to prevent flickering if data hasn't changed
        current_logs = self.hardware_controller.get_audit_logs()
        selected_ids = {
            self.audit_tree.item(row, "values")[0]
            for row in self.audit_tree.selection()
        }
        existing_ids = [self.audit_tree.item(item)["values"][0] for item in self.audit_tree.get_children()]
        new_ids = [log.get("id") for log in current_logs]

        if existing_ids == new_ids:
            return  # No structural change; keep tree intact

        for item in self.audit_tree.get_children():
            self.audit_tree.delete(item)

        for log in current_logs:
            action = str(log.get("action", "")).upper()
            action_tag = ""
            if "APPROVE" in action:
                action_tag = "approved"
            elif "DECLINE" in action:
                action_tag = "declined"
            elif "SUBMIT" in action:
                action_tag = "submitted"
            self.audit_tree.insert(
                "",
                "end",
                values=(
                    log.get("id"),
                    action,
                    log.get("details"),
                    log.get("performed_by", "System"),
                    log.get("timestamp"),
                    "[x]" if str(log.get("id")) in selected_ids else "[ ]"
                ),
                tags=(action_tag,)
            )
        for row in self.audit_tree.get_children():
            if str(self.audit_tree.item(row, "values")[0]) in selected_ids:
                self.audit_tree.selection_add(row)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an item to delete.")
            return

        item_ids = [self.tree.item(item, "values")[0] for item in selected]
        item_summary = ", ".join(item_ids)

        if messagebox.askyesno("Confirm Delete", f"Delete {len(item_ids)} selected item(s)?\n\n{item_summary}"):
            for item_id in item_ids:
                self.hardware_controller.delete_hardware(item_id, admin_username=self.admin_name)

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an item to edit.")
            return
        if len(selected) > 1:
            messagebox.showwarning("One Item at a Time", "Select only one item when editing hardware.")
            return

        item_values = self.tree.item(selected[0], "values")
        item_id, item_name, category, stock_qty, unit_price, _, condition, _ = item_values[:8]
        cleaned_unit_price = str(unit_price or "").replace("₱", "").replace(",", "").strip() or "0"

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Item {item_id}")
        dialog.configure(bg="#1E293B")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        form = ttk.Frame(dialog, style="Card.TFrame", padding=20)
        form.pack(fill="both", expand=True)

        ttk.Label(form, text=f"Edit Hardware Item {item_id}", style="Header.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 15)
        )
        ttk.Label(form, text="Item Name:", style="CardLabel.TLabel").grid(row=1, column=0, sticky="w", pady=6)
        name_entry = ttk.Entry(form, width=32)
        name_entry.insert(0, item_name)
        name_entry.grid(row=1, column=1, padx=(15, 0), pady=6, sticky="ew")

        ttk.Label(form, text="Category:", style="CardLabel.TLabel").grid(row=2, column=0, sticky="w", pady=6)
        category_entry = ttk.Entry(form, width=32)
        category_entry.insert(0, category)
        category_entry.grid(row=2, column=1, padx=(15, 0), pady=6, sticky="ew")

        ttk.Label(form, text="Stock Quantity:", style="CardLabel.TLabel").grid(row=3, column=0, sticky="w", pady=6)
        stock_entry = ttk.Spinbox(form, from_=0, to=100000, width=32)
        stock_entry.set(stock_qty)
        stock_entry.grid(row=3, column=1, padx=(15, 0), pady=6, sticky="ew")

        ttk.Label(form, text="Unit Price:", style="CardLabel.TLabel").grid(row=4, column=0, sticky="w", pady=6)
        price_entry = ttk.Entry(form, width=32)
        price_entry.insert(0, cleaned_unit_price)
        price_entry.grid(row=4, column=1, padx=(15, 0), pady=6, sticky="ew")

        ttk.Label(form, text="Condition:", style="CardLabel.TLabel").grid(row=5, column=0, sticky="w", pady=6)
        condition_entry = ttk.Combobox(form, values=["GOOD", "FAIR", "DAMAGED"], state="readonly", width=32)
        condition_entry.set(condition or "GOOD")
        condition_entry.grid(row=5, column=1, padx=(15, 0), pady=6, sticky="ew")

        def save_changes():
            name = name_entry.get().strip()
            updated_category = category_entry.get().strip()
            try:
                quantity = int(stock_entry.get())
                price = float(price_entry.get())
            except ValueError:
                messagebox.showerror("Invalid Quantity", "Stock quantity and unit price must be valid numbers.", parent=dialog)
                return

            if not name or not updated_category or quantity < 0 or price < 0:
                messagebox.showwarning("Missing Information", "Enter a name, category, valid stock quantity, and non-negative unit price.", parent=dialog)
                return

            if self.hardware_controller.update_hardware(
                item_id, name, updated_category, quantity, condition_entry.get(), self.admin_name, price
            ):
                dialog.destroy()
            else:
                messagebox.showerror("Update Failed", "The item could not be updated.", parent=dialog)

        ttk.Button(form, text="Save Changes", style="Primary.TButton", command=save_changes).grid(
            row=6, column=1, sticky="e", pady=(15, 0)
        )
        ttk.Button(form, text="Cancel", command=dialog.destroy).grid(
            row=6, column=0, sticky="w", pady=(15, 0)
        )

    def add_new_item(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Hardware Item")
        dialog.resizable(False, False)
        form = ttk.Frame(dialog, style="Card.TFrame", padding=20)
        form.pack(fill="both", expand=True)
        fields = {}
        for row, (label, key) in enumerate((("Hardware ID:", "id"), ("Name:", "name"), ("Category:", "category"), ("Quantity:", "quantity"), ("Unit Price:", "unit_price"))):
            ttk.Label(form, text=label, style="CardLabel.TLabel").grid(row=row, column=0, sticky="w", pady=6)
            fields[key] = ttk.Entry(form, width=32)
            fields[key].grid(row=row, column=1, padx=(15, 0), pady=6, sticky="ew")
        ttk.Label(form, text="Condition:", style="CardLabel.TLabel").grid(row=5, column=0, sticky="w", pady=6)
        condition = ttk.Combobox(form, values=["GOOD", "FAIR", "DAMAGED"], state="readonly", width=32)
        condition.set("GOOD")
        condition.grid(row=5, column=1, padx=(15, 0), pady=6, sticky="ew")

        def save_item():
            try:
                quantity = int(fields["quantity"].get())
                unit_price = float(fields["unit_price"].get())
            except ValueError:
                messagebox.showerror("Invalid Quantity", "Quantity and unit price must be valid numbers.", parent=dialog)
                return
            if not all(fields[key].get().strip() for key in ("id", "name", "category")) or quantity < 0 or unit_price < 0:
                messagebox.showwarning("Missing Information", "Enter an ID, name, category, valid quantity, and non-negative unit price.", parent=dialog)
                return
            self.hardware_controller.add_hardware(
                fields["id"].get().strip(),
                fields["name"].get().strip(),
                fields["category"].get().strip(),
                quantity,
                condition=condition.get(),
                admin_username=self.admin_name,
                unit_price=unit_price
            )
            dialog.destroy()

        ttk.Button(form, text="Save Item", style="Primary.TButton", command=save_item).grid(row=6, column=1, sticky="e", pady=(14, 0))

    def approve_selected_request(self):
        selected = self.req_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a request to approve.")
            return

        request_ids = [self.req_tree.item(item, "values")[0] for item in selected]
        if messagebox.askyesno("Confirm", f"Approve {len(request_ids)} selected request(s)?"):
            for request_id in request_ids:
                self.hardware_controller.update_request_status(request_id, "APPROVED", admin_username=self.admin_name)

    def decline_selected_request(self):
        selected = self.req_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a request to decline.")
            return

        request_ids = [self.req_tree.item(item, "values")[0] for item in selected]
        if messagebox.askyesno("Confirm", f"Decline {len(request_ids)} selected request(s)?"):
            for request_id in request_ids:
                self.hardware_controller.update_request_status(request_id, "DECLINED", admin_username=self.admin_name)

    def record_return(self):
        selected = self.req_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an approved request to record a return.")
            return
        if len(selected) > 1:
            messagebox.showwarning("One Request at a Time", "Select only one request when recording a return.")
            return

        request_id = self.req_tree.item(selected[0], "values")[0]
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Record Return #{request_id}")
        dialog.configure(bg=theme.BG_DARK)
        dialog.resizable(False, False)
        form = ttk.Frame(dialog, style="Card.TFrame", padding=20)
        form.pack(fill="both", expand=True)
        ttk.Label(form, text="Equipment Return", style="Header.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))
        ttk.Label(form, text="Condition:", style="CardLabel.TLabel").grid(row=1, column=0, sticky="w", pady=6)
        condition = ttk.Combobox(form, values=["GOOD", "FAIR", "DAMAGED"], state="readonly", width=27)
        condition.current(0)
        condition.grid(row=1, column=1, padx=(15, 0), pady=6)
        ttk.Label(form, text="Notes:", style="CardLabel.TLabel").grid(row=2, column=0, sticky="w", pady=6)
        notes = ttk.Entry(form, width=30)
        notes.grid(row=2, column=1, padx=(15, 0), pady=6)

        def save_return():
            if self.hardware_controller.return_request(request_id, condition.get(), notes.get().strip(), self.admin_name):
                dialog.destroy()
            else:
                messagebox.showerror("Return Failed", "Only approved or return-requested equipment can be recorded.", parent=dialog)

        ttk.Button(form, text="Save Return", style="Primary.TButton", command=save_return).grid(row=3, column=1, sticky="e", pady=(14, 0))