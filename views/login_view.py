import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from PIL import Image, ImageEnhance, ImageOps, ImageTk
import theme


class LoginWindow(ttk.Frame):
    def __init__(self, parent, auth_controller, on_login_success):
        super().__init__(parent)
        self.parent = parent
        self.auth_controller = auth_controller
        self.on_login_success = on_login_success
        self.show_password = False

        self.pack(fill="both", expand=True, padx=26, pady=26)
        self.show_login_form()

    def clear_view(self):
        for widget in self.winfo_children():
            widget.destroy()

    def show_login_form(self):
        self.clear_view()

        portal = ttk.Frame(self, style="Portal.TFrame", padding=10)
        portal.pack(fill="both", expand=True)

        brand = ttk.Frame(portal, style="Brand.TFrame", width=270, padding=28)
        brand.pack(side="left", fill="y")
        brand.pack_propagate(False)

        image_files = list(Path(__file__).resolve().parent.parent.glob("*.webp"))
        if image_files:
            campus_image = Image.open(image_files[0]).convert("RGB")
            campus_image = ImageOps.fit(campus_image, (270, 350), method=Image.Resampling.LANCZOS)
            campus_image = ImageEnhance.Brightness(campus_image).enhance(0.62)
            self.campus_photo = ImageTk.PhotoImage(campus_image)
            tk.Label(brand, image=self.campus_photo, borderwidth=0, bg=theme.BG_PAGE).place(x=0, y=300, relwidth=1, height=350)

        tk.Label(brand, text="NU", bg=theme.BG_PAGE, fg=theme.GOLD, font=("Georgia", 26, "bold")).pack(anchor="w", pady=(8, 20))
        tk.Label(brand, text="NATIONAL\nUNIVERSITY-\nMANILA", bg=theme.BG_PAGE, fg=theme.TEXT_LIGHT, font=("Segoe UI", 12, "bold"), justify="left").pack(anchor="w")
        tk.Frame(brand, height=3, width=52, bg=theme.GOLD).pack(anchor="w", pady=(20, 18))
        tk.Label(brand, text="Laboratory Asset\nManagement Portal", bg=theme.BG_PAGE, fg=theme.TEXT_MUTED, font=("Segoe UI", 10), justify="left").pack(anchor="w")
        tk.Label(brand, text="Learn. Lead. Serve.", bg=theme.BG_PAGE, fg=theme.TEXT_MUTED, font=("Segoe UI", 10), justify="left").pack(anchor="w", pady=(14, 0))

        card = ttk.Frame(portal, style="Card.TFrame", padding=34)
        card.pack(side="left", fill="both", expand=True)

        # Header Title configured with wraplength to prevent overflow/cutting off
        ttk.Label(
            card,
            text="COMPUTER ENGINEERING\nLABORATORY EQUIPMENT PORTAL",
            style="PortalTitle.TLabel",
            wraplength=600,
            justify="center"
        ).pack(anchor="center", pady=(0, 2))

        ttk.Label(
            card,
            text="Sign in to manage laboratory equipment",
            style="PortalIntro.TLabel",
            justify="center"
        ).pack(anchor="center", pady=(0, 24))

        form_frame = ttk.Frame(card, style="Card.TFrame")
        form_frame.pack(anchor="center")

        ttk.Label(form_frame, text="Username", style="CardLabel.TLabel").pack(anchor="w", pady=(2, 2))
        self.e_username = ttk.Entry(form_frame, font=("Segoe UI", 10), width=60)
        self.e_username.pack(fill="x", pady=(0, 10))
        self.e_username.focus()

        ttk.Label(form_frame, text="Password", style="CardLabel.TLabel").pack(anchor="w", pady=(2, 2))
        pass_frame = ttk.Frame(form_frame, style="Card.TFrame")
        pass_frame.pack(fill="x", pady=(0, 15))

        self.e_password = ttk.Entry(pass_frame, font=("Segoe UI", 10), show="•", width=60)
        self.e_password.pack(side="left", fill="x", expand=True)

        self.btn_show = ttk.Button(pass_frame, text="👁", width=3, command=self.toggle_password)
        self.btn_show.pack(side="right", padx=(5, 0))

        ttk.Button(form_frame, text="Login", style="Primary.TButton", command=self.handle_login).pack(fill="x", ipady=4, pady=(5, 10))

        link_frame = ttk.Frame(form_frame, style="Card.TFrame")
        link_frame.pack(fill="x", pady=(5, 0))

        lbl_reg = tk.Label(link_frame, text="Register Account", bg=theme.CARD_BG, fg=theme.ACCENT_BLUE, font=("Segoe UI", 9, "underline"), cursor="hand2")
        lbl_reg.pack(side="left")
        lbl_reg.bind("<Button-1>", lambda e: self.show_register_form())

        lbl_forgot = tk.Label(link_frame, text="Reset Password", bg=theme.CARD_BG, fg=theme.DANGER_RED, font=("Segoe UI", 9, "underline"), cursor="hand2")
        lbl_forgot.pack(side="right")
        lbl_forgot.bind("<Button-1>", lambda e: self.show_reset_form())

        self.parent.bind("<Return>", lambda e: self.handle_login())

    def toggle_password(self):
        self.show_password = not self.show_password
        self.e_password.config(show="" if self.show_password else "•")

    def handle_login(self):
        u = self.e_username.get().strip()
        p = self.e_password.get().strip()

        if not u or not p:
            messagebox.showwarning("Input Error", "Please fill in Username and Password.", parent=self)
            return

        ok, result = self.auth_controller.login_user(u, p)
        if ok:
            self.parent.unbind("<Return>")
            self.on_login_success(result)
        else:
            messagebox.showerror("Auth Error", result, parent=self)

    def create_form_shell(self):
        portal = ttk.Frame(self, style="Portal.TFrame", padding=10)
        portal.pack(fill="both", expand=True)

        brand = ttk.Frame(portal, style="Brand.TFrame", width=270, padding=28)
        brand.pack(side="left", fill="y")
        brand.pack_propagate(False)

        image_files = list(Path(__file__).resolve().parent.parent.glob("*.webp"))
        if image_files:
            campus_image = Image.open(image_files[0]).convert("RGB")
            campus_image = ImageOps.fit(campus_image, (270, 350), method=Image.Resampling.LANCZOS)
            campus_image = ImageEnhance.Brightness(campus_image).enhance(0.62)
            self.campus_photo = ImageTk.PhotoImage(campus_image)
            tk.Label(brand, image=self.campus_photo, borderwidth=0, bg=theme.BG_PAGE).place(x=0, y=300, relwidth=1, height=350)

        tk.Label(brand, text="NU", bg=theme.BG_PAGE, fg=theme.GOLD, font=("Georgia", 26, "bold")).pack(anchor="w", pady=(8, 20))
        tk.Label(brand, text="NATIONAL\nUNIVERSITY-\nMANILA", bg=theme.BG_PAGE, fg=theme.TEXT_LIGHT, font=("Segoe UI", 12, "bold"), justify="left").pack(anchor="w")
        tk.Frame(brand, height=3, width=52, bg=theme.GOLD).pack(anchor="w", pady=(20, 18))
        tk.Label(brand, text="Laboratory Asset\nManagement Portal", bg=theme.BG_PAGE, fg=theme.TEXT_MUTED, font=("Segoe UI", 10), justify="left").pack(anchor="w")
        tk.Label(brand, text="Learn. Lead. Serve.", bg=theme.BG_PAGE, fg=theme.TEXT_MUTED, font=("Segoe UI", 10), justify="left").pack(anchor="w", pady=(14, 0))

        card = ttk.Frame(portal, style="Card.TFrame", padding=50)
        card.pack(side="left", fill="both", expand=True)
        return card

    def show_register_form(self):
        self.clear_view()

        card = self.create_form_shell()

        ttk.Label(card, text="Create your account", style="PortalTitle.TLabel").pack(anchor="w", pady=(0, 3))
        ttk.Label(card, text="Register for access to the laboratory equipment portal.", style="PortalIntro.TLabel").pack(anchor="w", pady=(0, 20))

        ttk.Label(card, text="Username", style="CardLabel.TLabel").pack(anchor="w", pady=(2, 2))
        self.reg_username = ttk.Entry(card, font=("Segoe UI", 10), width=60)
        self.reg_username.pack(anchor="w", pady=(0, 8))

        ttk.Label(card, text="Email Address", style="CardLabel.TLabel").pack(anchor="w", pady=(2, 2))
        self.reg_email = ttk.Entry(card, font=("Segoe UI", 10), width=60)
        self.reg_email.pack(anchor="w", pady=(0, 8))

        ttk.Label(card, text="Password", style="CardLabel.TLabel").pack(anchor="w", pady=(2, 2))
        self.reg_password = ttk.Entry(card, font=("Segoe UI", 10), show="•", width=60)
        self.reg_password.pack(anchor="w", pady=(0, 8))

        ttk.Label(card, text="Recovery Keyword", style="CardLabel.TLabel").pack(anchor="w", pady=(2, 2))
        self.reg_keyword = ttk.Entry(card, font=("Segoe UI", 10), width=60)
        self.reg_keyword.pack(anchor="w", pady=(0, 8))

        ttk.Label(card, text="Role", style="CardLabel.TLabel").pack(anchor="w", pady=(2, 2))
        self.reg_role = ttk.Combobox(card, values=["STUDENT", "ADMIN"], state="readonly", font=("Segoe UI", 10), width=60)
        self.reg_role.current(0)
        self.reg_role.pack(fill="x", pady=(0, 15))

        ttk.Button(card, text="Sign Up", style="Primary.TButton", command=self.handle_register).pack(fill="x", ipady=4)

        lbl_back = tk.Label(card, text="Back to Login", bg=theme.CARD_BG, fg=theme.TEXT_MUTED, font=("Segoe UI", 9, "underline"), cursor="hand2")
        lbl_back.pack(anchor="center", pady=(12, 0))
        lbl_back.bind("<Button-1>", lambda e: self.show_login_form())

    def handle_register(self):
        u = self.reg_username.get().strip()
        e = self.reg_email.get().strip()
        p = self.reg_password.get().strip()
        k = self.reg_keyword.get().strip()
        r = self.reg_role.get()

        if not u or not e or not p or not k or not r:
            messagebox.showwarning("Error", "All fields are required.", parent=self)
            return

        if "@" not in e or "." not in e:
            messagebox.showerror("Invalid Email", "Please enter a valid email address.", parent=self)
            return

        ok, msg = self.auth_controller.register_user(u, e, p, k, r)
        if ok:
            messagebox.showinfo("Success", msg, parent=self)
            self.show_login_form()
        else:
            messagebox.showerror("Registration Error", msg, parent=self)

    def show_reset_form(self):
        self.clear_view()

        card = self.create_form_shell()

        ttk.Label(card, text="Reset your password", style="PortalTitle.TLabel").pack(anchor="w", pady=(0, 3))
        ttk.Label(card, text="Verify your account details to regain access.", style="PortalIntro.TLabel").pack(anchor="w", pady=(0, 20))

        ttk.Label(card, text="Username", style="CardLabel.TLabel").pack(anchor="w", pady=(2, 2))
        self.rst_username = ttk.Entry(card, font=("Segoe UI", 10), width=60)
        self.rst_username.pack(anchor="w", pady=(0, 8))

        ttk.Label(card, text="Registered Email", style="CardLabel.TLabel").pack(anchor="w", pady=(2, 2))
        self.rst_email = ttk.Entry(card, font=("Segoe UI", 10), width=60)
        self.rst_email.pack(anchor="w", pady=(0, 8))

        ttk.Label(card, text="Recovery Keyword", style="CardLabel.TLabel").pack(anchor="w", pady=(2, 2))
        self.rst_keyword = ttk.Entry(card, font=("Segoe UI", 10), width=60)
        self.rst_keyword.pack(anchor="w", pady=(0, 8))

        ttk.Label(card, text="New Password", style="CardLabel.TLabel").pack(anchor="w", pady=(2, 2))
        self.rst_password = ttk.Entry(card, font=("Segoe UI", 10), show="•", width=60)
        self.rst_password.pack(anchor="w", pady=(0, 15))

        ttk.Button(card, text="Reset & Unlock Account", style="Primary.TButton", command=self.handle_reset).pack(fill="x", ipady=4)

        lbl_back = tk.Label(card, text="Back to Login", bg=theme.CARD_BG, fg=theme.TEXT_MUTED, font=("Segoe UI", 9, "underline"), cursor="hand2")
        lbl_back.pack(anchor="center", pady=(12, 0))
        lbl_back.bind("<Button-1>", lambda e: self.show_login_form())

    def handle_reset(self):
        u = self.rst_username.get().strip()
        e = self.rst_email.get().strip()
        k = self.rst_keyword.get().strip()
        p = self.rst_password.get().strip()

        if not u or not e or not k or not p:
            messagebox.showwarning("Error", "All fields are required.", parent=self)
            return

        ok, msg = self.auth_controller.reset_password(u, e, k, p)
        if ok:
            messagebox.showinfo("Reset Complete", msg, parent=self)
            self.show_login_form()
        else:
            messagebox.showerror("Error", msg, parent=self)