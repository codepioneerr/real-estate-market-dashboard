"""
Step 1: Load cleaned CSVs into a SQLite database (data/real_estate.db).
Run after clean_data.py.
"""

import os
import sqlite3
import pandas as pd

BASE = os.path.join(os.path.dirname(__file__), "..")
CLEAN_DIR = os.path.join(BASE, "data", "cleaned")
DB_PATH = os.path.join(BASE, "data", "real_estate.db")


def get_conn():
    return sqlite3.connect(DB_PATH)


def load_table(conn, csv_name, table_name, parse_dates=None):
    path = os.path.join(CLEAN_DIR, csv_name)
    if not os.path.exists(path):
        print(f"  [skip] {csv_name} not found")
        return
    df = pd.read_csv(path, parse_dates=parse_dates)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    print(f"  Loaded {len(df):,} rows → {table_name}")


if __name__ == "__main__":
    print(f"Writing to {DB_PATH}")
    conn = get_conn()

    load_table(conn, "rents_clean.csv",        "rents",        parse_dates=["date"])
    load_table(conn, "vacancy_clean.csv",       "vacancy")
    load_table(conn, "income_clean.csv",        "income")
    load_table(conn, "affordability_clean.csv", "affordability")

    # Persist schema version for future migrations
    conn.execute(
        "CREATE TABLE IF NOT EXISTS _meta (key TEXT PRIMARY KEY, value TEXT)"
    )
    conn.execute(
        "INSERT OR REPLACE INTO _meta VALUES ('schema_version', '1')"
    )
    conn.commit()
    conn.close()

    print(f"\nDatabase ready: {DB_PATH}")
    print("Run scripts/query_data.py to explore it.")
