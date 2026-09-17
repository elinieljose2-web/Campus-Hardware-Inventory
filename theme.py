import tkinter as tk
from tkinter import ttk

# National University-inspired palette
BG_DARK = "#071B33"
BG_PAGE = "#EEF3F8"
CARD_BG = "#FFFFFF"
TEXT_LIGHT = "#102A43"
TEXT_MUTED = "#52677D"
ACCENT_BLUE = "#0066B3"
ACCENT_HOVER = "#004F8A"
DANGER_RED = "#C83C4A"
BORDER_COLOR = "#C9D6E2"
GOLD = "#F4B41A"
BRAND_NAVY = "#0B2D50"
SUCCESS_BG = "#DFF5E5"
SUCCESS_TEXT = "#1E7E4D"


def apply_global_theme(root):
    root.configure(bg=BG_PAGE)
    style = ttk.Style()
    style.theme_use("clam")

    # Global defaults
    style.configure(".", font=("Segoe UI", 10))
    style.configure("TFrame", background=BG_PAGE)
    style.configure("Topbar.TFrame", background=BG_DARK)
    style.configure("Card.TFrame", background=CARD_BG, relief="flat")
    style.configure("Panel.TFrame", background=BG_PAGE, relief="flat")
    style.configure("Portal.TFrame", background="#EAF1F7", relief="flat")
    style.configure("Brand.TFrame", background=BG_PAGE, relief="flat")

    # Label Styling
    style.configure("TLabel", background=BG_PAGE, foreground=TEXT_LIGHT, font=("Segoe UI", 10))
    style.configure("Card.TLabel", background=CARD_BG, foreground=TEXT_LIGHT, font=("Segoe UI", 10))
    style.configure("Portal.TLabel", background="#EAF1F7", foreground=TEXT_LIGHT, font=("Segoe UI", 10))
    style.configure("Muted.TLabel", background=BG_PAGE, foreground=TEXT_MUTED, font=("Segoe UI", 9))
    style.configure("Dark.TLabel", background=BG_DARK, foreground="#F8FAFC", font=("Segoe UI", 10))
    style.configure("Header.TLabel", background=CARD_BG, foreground=TEXT_LIGHT, font=("Segoe UI", 14, "bold"))
    style.configure("Title.TLabel", background=BG_PAGE, foreground=TEXT_LIGHT, font=("Segoe UI", 16, "bold"))
    style.configure("Welcome.TLabel", background=BG_PAGE, foreground=GOLD, font=("Segoe UI", 10, "bold"), justify="left")
    style.configure("WelcomeName.TLabel", background=BG_DARK, foreground="#F8FAFC", font=("Segoe UI", 10, "bold"))
    style.configure("CardLabel.TLabel", background=CARD_BG, foreground=TEXT_MUTED, font=("Segoe UI", 9, "bold"))
    style.configure("PortalTitle.TLabel", background=CARD_BG, foreground=TEXT_LIGHT, font=("Georgia", 19, "bold"))
    style.configure("BrandMark.TLabel", background=BG_DARK, foreground=GOLD, font=("Georgia", 26, "bold"))
    style.configure("BrandName.TLabel", background=BG_DARK, foreground="#FFFFFF", font=("Segoe UI", 12, "bold"))
    style.configure("BrandSub.TLabel", background=BG_DARK, foreground="#D6E4F0", font=("Segoe UI", 10))
    style.configure("PortalIntro.TLabel", background=CARD_BG, foreground=TEXT_MUTED, font=("Segoe UI", 10))
    style.configure("PortalLabel.TLabel", background="#EAF1F7", foreground=TEXT_MUTED, font=("Segoe UI", 9))
    style.configure("PortalHeading.TLabel", background="#EAF1F7", foreground=TEXT_LIGHT, font=("Segoe UI", 10, "bold"))
    style.configure("MetricValue.TLabel", background=CARD_BG, foreground=TEXT_LIGHT, font=("Segoe UI", 14, "bold"))
    style.configure("MetricLabel.TLabel", background=CARD_BG, foreground=TEXT_MUTED, font=("Segoe UI", 9))
    style.configure("Success.TLabel", background=SUCCESS_BG, foreground=SUCCESS_TEXT, font=("Segoe UI", 10, "bold"))

    # Entry Fields & Comboboxes
    style.configure("TEntry", fieldbackground="#F7FAFC", foreground=TEXT_LIGHT, insertcolor=TEXT_LIGHT, borderwidth=1, relief="solid")
    style.configure("TCombobox", fieldbackground="#F7FAFC", foreground=TEXT_LIGHT, borderwidth=1)
    style.configure("TSpinbox", fieldbackground="#F7FAFC", foreground=TEXT_LIGHT, borderwidth=1)

    # Buttons
    style.configure("TButton", padding=[10, 6], borderwidth=0, relief="flat")
    style.configure("Primary.TButton", background=ACCENT_BLUE, foreground="white", font=("Segoe UI", 9, "bold"), borderwidth=0, padding=[14, 9])
    style.map("Primary.TButton", background=[("active", ACCENT_HOVER), ("pressed", ACCENT_HOVER)], foreground=[("active", "white"), ("pressed", "white")])

    style.configure("Danger.TButton", background=DANGER_RED, foreground="white", font=("Segoe UI", 9, "bold"), borderwidth=0, padding=[14, 9])
    style.map("Danger.TButton", background=[("active", "#DC2626"), ("pressed", "#DC2626")], foreground=[("active", "white"), ("pressed", "white")])

    style.configure("Nav.TButton", background=BG_DARK, foreground="#FFFFFF", font=("Segoe UI", 9, "bold"), borderwidth=0, padding=[10, 7])
    style.map("Nav.TButton", background=[("active", "#123D63"), ("pressed", "#123D63")], foreground=[("active", "white"), ("pressed", "white")])

    # Notebook Tabs
    style.configure("TNotebook", background=BG_PAGE, borderwidth=0)
    style.configure("TNotebook.Tab", background=CARD_BG, foreground=TEXT_MUTED, padding=[16, 9], font=("Segoe UI", 9, "bold"))
    style.map("TNotebook.Tab", background=[("selected", ACCENT_BLUE), ("active", BORDER_COLOR)], foreground=[("selected", "#FFFFFF"), ("active", TEXT_LIGHT)])

    # Treeview Tables
    style.configure("Treeview", background=CARD_BG, foreground=TEXT_LIGHT, fieldbackground=CARD_BG, rowheight=30, font=("Segoe UI", 9))
    style.map("Treeview", background=[("selected", BORDER_COLOR)], foreground=[("selected", TEXT_LIGHT)])
    style.configure("Treeview.Heading", background=BG_DARK, foreground="#F8FAFC", font=("Segoe UI", 9, "bold"))
    style.map("Treeview", background=[("selected", BORDER_COLOR)])