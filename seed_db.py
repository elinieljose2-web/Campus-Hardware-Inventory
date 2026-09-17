import sqlite3

def seed_database():
    conn = sqlite3.connect("hardware_inventory.db")
    cursor = conn.cursor()

    # Re-create table using the current app schema
    cursor.execute("DROP TABLE IF EXISTS hardware")
    cursor.execute("""
        CREATE TABLE hardware (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            stock_qty INTEGER NOT NULL,
            unit_price REAL DEFAULT 0.0,
            status TEXT DEFAULT 'In Stock',
            condition_status TEXT DEFAULT 'GOOD'
        )
    """)

    # 20 Laboratory Items with sample unit prices for the asset dashboard
    equipment = [
        ("HW-101", "Digital Multimeter", "Measurement", 15, 1500.00, "In Stock", "GOOD"),
        ("HW-102", "Oscilloscope", "Measurement", 8, 2500.00, "In Stock", "GOOD"),
        ("HW-103", "DC Power Supply", "Power Supply", 10, 1800.00, "In Stock", "GOOD"),
        ("HW-104", "Function Generator", "Measurement", 6, 3200.00, "In Stock", "GOOD"),
        ("HW-105", "Breadboard", "Prototyping", 40, 250.00, "In Stock", "GOOD"),
        ("HW-106", "Arduino Uno", "Microcontroller", 25, 450.00, "In Stock", "GOOD"),
        ("HW-107", "PIC16F877A IC", "Microcontroller", 30, 120.00, "In Stock", "GOOD"),
        ("HW-108", "Logic Analyzer", "Measurement", 5, 4800.00, "In Stock", "GOOD"),
        ("HW-109", "7-Segment Display", "Display", 50, 80.00, "In Stock", "GOOD"),
        ("HW-110", "74HC08 (AND Gate)", "Digital IC", 50, 18.00, "In Stock", "GOOD"),
        ("HW-111", "74HC32 (OR Gate)", "Digital IC", 50, 18.00, "In Stock", "GOOD"),
        ("HW-112", "74HC04 (NOT Gate)", "Digital IC", 50, 18.00, "In Stock", "GOOD"),
        ("HW-113", "74HC00 (NAND Gate)", "Digital IC", 50, 18.00, "In Stock", "GOOD"),
        ("HW-114", "74HC138 (Decoder)", "Digital IC", 30, 70.00, "In Stock", "GOOD"),
        ("HW-115", "74HC151 (MUX)", "Digital IC", 30, 80.00, "In Stock", "GOOD"),
        ("HW-116", "PICKit 3 Programmer", "Programmer", 10, 950.00, "In Stock", "GOOD"),
        ("HW-117", "Soldering Iron", "Tools", 12, 350.00, "In Stock", "GOOD"),
        ("HW-118", "Jumper Wires", "Accessories", 100, 90.00, "In Stock", "GOOD"),
        ("HW-119", "16x2 LCD Module", "Display", 20, 180.00, "In Stock", "GOOD"),
        ("HW-120", "Wire Stripper", "Tools", 15, 200.00, "In Stock", "GOOD")
    ]

    cursor.executemany("""
        INSERT INTO hardware (id, name, category, stock_qty, unit_price, status, condition_status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, equipment)

    conn.commit()
    conn.close()
    print("Database updated with 20 items successfully!")

if __name__ == "__main__":
    seed_database()