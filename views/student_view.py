import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import theme

class StudentReservationWindow:
    def __init__(self, root, user, hardware_controller, logout_callback):
        self.root = root
        self.user = user
        self.hardware_controller = hardware_controller
        self.logout_callback = logout_callback

        self.setup_ui()
        self.load_hardware_options()

    def setup_ui(self):
        username = self.user.get("username", "Student") if isinstance(self.user, dict) else str(self.user)

        # Top navigation bar
        topbar = ttk.Frame(self.root, style="Topbar.TFrame")
        topbar.pack(fill="x")

        brand_frame = ttk.Frame(topbar, style="Topbar.TFrame")
        brand_frame.pack(side="left", padx=(20, 0), pady=12)
        ttk.Label(brand_frame, text="NU", style="BrandMark.TLabel").pack(side="left")
        ttk.Label(brand_frame, text="NU Hardware Inventory", style="BrandName.TLabel").pack(side="left", padx=(10, 0))

        actions = ttk.Frame(topbar, style="Topbar.TFrame")
        actions.pack(side="right", padx=20, pady=12)
        ttk.Button(actions, text="Dashboard", style="Nav.TButton", command=lambda: None).pack(side="left", padx=(0, 8))
        ttk.Label(actions, text=f"{username[:1].upper()}", style="WelcomeName.TLabel", width=2).pack(side="left")
        ttk.Label(actions, text=f"{username}", style="BrandSub.TLabel").pack(side="left", padx=(6, 12))
        ttk.Button(actions, text="Logout", style="Nav.TButton", command=self.logout_callback).pack(side="left")

        success_banner = ttk.Label(self.root, text="✓ Login successful!", style="Success.TLabel", anchor="w")
        success_banner.pack(fill="x", padx=20, pady=(14, 0))

        title_row = tk.Frame(self.root, bg=theme.BG_PAGE)
        title_row.pack(fill="x", padx=20, pady=(18, 12))

        title_group = tk.Frame(title_row, bg=theme.BG_PAGE)
        title_group.pack(side="left", anchor="w")
        ttk.Label(title_group, text="Laboratory Dashboard", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_group, text=f"Good day, {username}!", style="Welcome.TLabel").pack(anchor="w", pady=(4, 0))

        action_group = tk.Frame(title_row, bg=theme.BG_PAGE)
        action_group.pack(side="right")
        self.notification_button = ttk.Button(action_group, text="Notifications (0)", style="Primary.TButton", command=self.show_notifications)
        self.update_notifications_button()
        self.notification_button.pack(side="right", padx=(0, 8))
        ttk.Button(action_group, text="My Requests", style="Primary.TButton", command=self.show_request_history).pack(side="right", padx=(0, 8))

        # Main content area keeps the form and portal guidance balanced.
        card_frame = tk.Frame(self.root, bg=theme.CARD_BG, padx=24, pady=24)
        card_frame.pack(fill="both", expand=True, padx=20, pady=(0, 25))

        form_frame = tk.Frame(card_frame, bg=theme.CARD_BG, padx=8, pady=8)
        form_frame.pack(side="left", fill="y", padx=(0, 34))

        info_panel = tk.Frame(card_frame, bg="#EAF1F7", padx=22, pady=22)
        info_panel.pack(side="right", fill="both", expand=True)
        ttk.Label(info_panel, text="STUDENT SERVICES", style="PortalHeading.TLabel").pack(anchor="w", pady=(4, 10))
        ttk.Label(
            info_panel,
            text="Equipment Request Rules",
            style="PortalTitle.TLabel",
            wraplength=250,
            justify="left"
        ).pack(anchor="w")
        tk.Frame(info_panel, height=3, width=48, bg=theme.GOLD).pack(anchor="w", pady=(16, 18))
        ttk.Label(
            info_panel,
            text="Please review these guidelines before submitting your request.",
            style="PortalLabel.TLabel",
            wraplength=250,
            justify="left"
        ).pack(anchor="w", pady=(0, 16))

        for number, rule in (
            ("01", "Select only equipment currently shown as available."),
            ("02", "State the purpose and instructor accurately."),
            ("03", "Request only the quantity needed for your activity."),
            ("04", "Handle all equipment carefully and responsibly."),
            ("05", "Return borrowed equipment on the agreed date."),
        ):
            rule_frame = ttk.Frame(info_panel, style="Portal.TFrame")
            rule_frame.pack(fill="x", pady=(0, 8))
            ttk.Label(rule_frame, text=number, style="PortalHeading.TLabel", width=3).pack(side="left", anchor="n")
            ttk.Label(rule_frame, text=rule, style="PortalLabel.TLabel", wraplength=215, justify="left").pack(side="left", fill="x", expand=True)

        section_title = ttk.Label(
            form_frame, 
            text="Borrower Information", 
            style="Header.TLabel"
        )
        section_title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))

        # 1. Borrower Name
        ttk.Label(form_frame, text="Borrower Name:", style="CardLabel.TLabel").grid(row=1, column=0, sticky="w", pady=8)
        self.borrower_entry = ttk.Entry(form_frame, width=32)
        self.borrower_entry.insert(0, username)
        self.borrower_entry.config(state="readonly")
        self.borrower_entry.grid(row=1, column=1, sticky="w", padx=15, pady=8)

        # 2. Item to Borrow
        ttk.Label(form_frame, text="Item to Borrow:", style="CardLabel.TLabel").grid(row=2, column=0, sticky="w", pady=8)
        self.item_combobox = ttk.Combobox(form_frame, width=30, state="readonly")
        self.item_combobox.grid(row=2, column=1, sticky="w", padx=15, pady=8)

        # 3. Quantity
        ttk.Label(form_frame, text="Quantity:", style="CardLabel.TLabel").grid(row=3, column=0, sticky="w", pady=8)
        self.qty_spinbox = ttk.Spinbox(form_frame, from_=1, to=20, width=10)
        self.qty_spinbox.set(1)
        self.qty_spinbox.grid(row=3, column=1, sticky="w", padx=15, pady=8)

        # 4. Date of Borrow
        ttk.Label(form_frame, text="Date of Borrow:", style="CardLabel.TLabel").grid(row=4, column=0, sticky="w", pady=8)
        self.date_entry = ttk.Entry(form_frame, width=32)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.grid(row=4, column=1, sticky="w", padx=15, pady=8)

        ttk.Label(form_frame, text="Return Due Date:", style="CardLabel.TLabel").grid(row=5, column=0, sticky="w", pady=8)
        self.due_date_entry = ttk.Entry(form_frame, width=32)
        self.due_date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.due_date_entry.grid(row=5, column=1, sticky="w", padx=15, pady=8)

        # 5. Purpose
        ttk.Label(form_frame, text="Purpose:", style="CardLabel.TLabel").grid(row=6, column=0, sticky="w", pady=8)
        self.purpose_entry = ttk.Entry(form_frame, width=32)
        self.purpose_entry.grid(row=6, column=1, sticky="w", padx=15, pady=8)

        # 6. Instructor
        ttk.Label(form_frame, text="Instructor:", style="CardLabel.TLabel").grid(row=7, column=0, sticky="w", pady=8)
        self.instructor_entry = ttk.Entry(form_frame, width=32)
        self.instructor_entry.grid(row=7, column=1, sticky="w", padx=15, pady=8)

        # Submit Button
        submit_btn = ttk.Button(
            form_frame, 
            text="Submit Reservation", 
            style="Primary.TButton",
            command=self.submit_reservation
        )
        submit_btn.grid(row=8, column=1, sticky="e", pady=(15, 0))

    def load_hardware_options(self):
        hardware_data = self.hardware_controller.get_all_hardware()
        options = []
        for hw in hardware_data:
            qty = hw.get("stock_qty", hw.get("quantity", 0))
            if qty > 0:
                options.append(f"{hw['id']} - {hw['name']}")

        self.item_combobox['values'] = options
        if options:
            self.item_combobox.current(0)

    def update_notifications_button(self):
        username = self.user.get("username", "") if isinstance(self.user, dict) else str(self.user)
        count = len(self.hardware_controller.get_notifications(username))
        if hasattr(self, "notification_button"):
            self.notification_button.configure(text=f"Notifications ({count})")

    def show_notifications(self):
        username = self.user.get("username", "") if isinstance(self.user, dict) else str(self.user)
        notifications = self.hardware_controller.get_all_notifications(username)
        if not notifications:
            notifications = [{"id": 0, "message": "You have no notifications.", "read": True}]

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
                        self.hardware_controller.mark_notification_read(notification_id, username),
                        self.update_notifications_button(),
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

    def show_request_history(self):
        username = self.user.get("username", "") if isinstance(self.user, dict) else str(self.user)
        history = tk.Toplevel(self.root)
        history.title("My Equipment Requests")
        history.geometry("760x520")
        history.configure(bg=theme.BG_PAGE)
        history.resizable(False, False)
        history.transient(self.root)
        history.grab_set()

        outer = tk.Frame(history, bg=theme.BG_PAGE, padx=18, pady=18)
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg=theme.BG_DARK, padx=18, pady=18)
        header.pack(fill="x")
        tk.Label(header, text="My Equipment Requests", bg=theme.BG_DARK, fg="white", font=("Segoe UI", 18, "bold")).pack(anchor="w")

        info = tk.Label(outer, text="Select an APPROVED request to begin the return process.", bg=theme.BG_PAGE, fg=theme.TEXT_MUTED, font=("Segoe UI", 10), anchor="w")
        info.pack(fill="x", pady=(14, 10))

        table_frame = tk.Frame(outer, bg=theme.CARD_BG, highlightthickness=1, highlightbackground=theme.BORDER_COLOR)
        table_frame.pack(fill="both", expand=True)

        columns = ("id", "hardware", "quantity", "date", "status", "condition")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        headings = {"id": "ID", "hardware": "Equipment", "quantity": "Qty", "date": "Request Date", "status": "Status", "condition": "Return Condition"}
        widths = {"id": 45, "hardware": 120, "quantity": 55, "date": 105, "status": 95, "condition": 125}
        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=widths[column], anchor="center")
        tree.tag_configure("approved", foreground="#16803C")
        tree.tag_configure("declined", foreground=theme.DANGER_RED)
        tree.tag_configure("submitted", foreground="#A56800")
        tree.tag_configure("return_requested", foreground="#7C3AED")
        for request in self.hardware_controller.get_requests_by_username(username):
            status = str(request.get("status", "")).upper()
            tag = {"APPROVED": "approved", "DECLINED": "declined", "PENDING": "submitted", "RETURN_REQUESTED": "return_requested"}.get(status, "")
            tree.insert("", "end", values=(request.get("id"), request.get("hardware_id"), request.get("borrow_qty"), request.get("borrow_date"), status, request.get("return_condition") or "-"), tags=(tag,))
        tree.pack(fill="both", expand=True, padx=1, pady=1)

        legend = tk.Frame(outer, bg=theme.BG_DARK, padx=18, pady=10)
        legend.pack(fill="x", pady=(14, 10))
        tk.Label(legend, text="STATUS:", bg=theme.BG_DARK, fg="white", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 12))
        for label, color in (("Approved", "#16803C"), ("Declined", theme.DANGER_RED), ("Submitted", "#A56800"), ("Return requested", "#7C3AED")):
            item = tk.Frame(legend, bg=theme.BG_DARK)
            item.pack(side="left", padx=(0, 14))
            tk.Label(item, text="●", bg=theme.BG_DARK, fg=color, font=("Segoe UI", 12, "bold")).pack(side="left")
            tk.Label(item, text=label, bg=theme.BG_DARK, fg="#EAF1F7", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(3, 0))

        actions = tk.Frame(outer, bg=theme.BG_PAGE)
        actions.pack(fill="x")

        def request_selected_return():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Select Request", "Select an approved request first.", parent=history)
                return
            request_id = tree.item(selected[0], "values")[0]
            status = tree.item(selected[0], "values")[4]
            if status != "APPROVED":
                messagebox.showinfo("Return Unavailable", "Only approved equipment can be returned.", parent=history)
                return
            if self.hardware_controller.request_return(request_id, username):
                messagebox.showinfo("Return Requested", "Your return request was sent to the laboratory administrator.", parent=history)
                history.destroy()
            else:
                messagebox.showerror("Return Error", "The return request could not be submitted.", parent=history)

        tk.Button(
            actions,
            text="Request Return",
            bg=theme.ACCENT_BLUE,
            fg="white",
            bd=0,
            highlightthickness=0,
            padx=20,
            pady=10,
            font=("Segoe UI", 10, "bold"),
            command=request_selected_return
        ).pack(side="right")

        history.protocol("WM_DELETE_WINDOW", history.destroy)

    def submit_reservation(self):
        selected_item = self.item_combobox.get()
        quantity = self.qty_spinbox.get()
        date_borrow = self.date_entry.get().strip()
        due_date = self.due_date_entry.get().strip()
        purpose = self.purpose_entry.get().strip()
        instructor = self.instructor_entry.get().strip()

        if not selected_item:
            messagebox.showwarning("Warning", "Please select an item to borrow.")
            return

        if not purpose or not instructor or not date_borrow or not due_date:
            messagebox.showwarning("Missing Information", "Please fill in all fields before submitting.")
            return

        hardware_id = selected_item.split(" - ")[0]
        username = self.borrower_entry.get()

        if hasattr(self.hardware_controller, "create_reservation"):
            success = self.hardware_controller.create_reservation(
                username=username,
                hardware_id=hardware_id,
                borrow_qty=int(quantity),
                borrow_date=date_borrow,
                purpose=purpose,
                instructor=instructor,
                return_due_date=due_date
            )
            if success:
                messagebox.showinfo("Success", f"Reservation request submitted successfully!\n\nItem: {selected_item}\nQty: {quantity}")
                self.purpose_entry.delete(0, tk.END)
                self.instructor_entry.delete(0, tk.END)
            else:
                messagebox.showerror("Error", "Failed to process reservation request.")
        else:
            messagebox.showerror("Error", "Controller method 'create_reservation' is missing.")