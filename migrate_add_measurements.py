"""
migrate_add_measurements.py

One-time migration script. Adds the new measurement + billing columns to
an EXISTING tailoring.db without deleting any current orders/customers.

Safe to run more than once -- it checks which columns already exist and
only adds the ones that are missing.

Run with:
    python migrate_add_measurements.py
"""

import os
import sqlite3

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "tailoring.db")

NEW_MEASUREMENT_COLUMNS = {
    "shoulder": "FLOAT",
    "arm_hole": "FLOAT",
    "chest": "FLOAT",
    "upper_chest": "FLOAT",
    "under_bust": "FLOAT",
    "waist": "FLOAT",
    "waist_length": "FLOAT",
    "natural_waist": "FLOAT",
    "hip": "FLOAT",
    "waist_to_knee": "FLOAT",
    "waist_to_ankle": "FLOAT",
    "waist_to_calf": "FLOAT",
    "length": "FLOAT",
    "kurti_length": "FLOAT",
    "pant_length": "FLOAT",
    "leg_round": "FLOAT",
    "sleeve_length": "FLOAT",
    "sleeve_round": "FLOAT",
    "front_neck": "FLOAT",
    "back_neck": "FLOAT",
    "neck": "FLOAT",
}

NEW_ORDER_COLUMNS = {
    "stitching_charge": "FLOAT DEFAULT 0.0",
    "lining_charge": "FLOAT DEFAULT 0.0",
}


def get_existing_columns(cursor, table):
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def add_missing_columns(cursor, table, wanted_columns):
    existing = get_existing_columns(cursor, table)
    added = []
    for col_name, col_type in wanted_columns.items():
        if col_name not in existing:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
            added.append(col_name)
    return added


def main():
    if not os.path.exists(DB_PATH):
        print(f"No database found at {DB_PATH}. Nothing to migrate — "
              f"just run the app normally and it will be created fresh "
              f"with all fields already included.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    added_m = add_missing_columns(cursor, "order_measurements", NEW_MEASUREMENT_COLUMNS)
    added_o = add_missing_columns(cursor, "orders", NEW_ORDER_COLUMNS)

    conn.commit()
    conn.close()

    if not added_m and not added_o:
        print("Nothing to do — database already has all the new columns.")
    else:
        if added_m:
            print(f"Added to order_measurements: {', '.join(added_m)}")
        if added_o:
            print(f"Added to orders: {', '.join(added_o)}")
        print("Migration complete. Your existing orders/customers are untouched.")


if __name__ == "__main__":
    main()
