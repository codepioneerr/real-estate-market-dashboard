"""
Step 1 (cont): SQL analytics on real_estate.db.
Demonstrates window functions, ranked markets, and trend queries.
Run after load_to_sql.py.
"""

import os
import sqlite3
import pandas as pd

BASE = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(BASE, "data", "real_estate.db")


def run(conn, title, sql):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)
    df = pd.read_sql_query(sql, conn)
    print(df.to_string(index=False))


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}\n"
            "Run scripts/load_to_sql.py first."
        )

    conn = sqlite3.connect(DB_PATH)

    run(conn, "Latest rent by city", """
        SELECT City,
               ROUND(AvgRent, 2) AS AvgRent,
               ROUND(MoMChange, 2) AS MoM_pct,
               ROUND(YoYChange, 2) AS YoY_pct
        FROM rents
        WHERE date = (SELECT MAX(date) FROM rents WHERE rents.City = rents.City)
        GROUP BY City
        ORDER BY AvgRent DESC
    """)

    run(conn, "12-month rolling average rent (window function)", """
        SELECT City,
               date,
               ROUND(AvgRent, 2) AS AvgRent,
               ROUND(AVG(AvgRent) OVER (
                   PARTITION BY City
                   ORDER BY date
                   ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
               ), 2) AS Rolling12m
        FROM rents
        ORDER BY City, date DESC
        LIMIT 12
    """)

    run(conn, "Best YoY growth months per city (top 3 each)", """
        SELECT City, date, YoY_pct, rnk FROM (
            SELECT City, date, ROUND(YoYChange, 2) AS YoY_pct,
                   RANK() OVER (PARTITION BY City ORDER BY YoYChange DESC) AS rnk
            FROM rents
            WHERE YoYChange IS NOT NULL
        ) WHERE rnk <= 3
        ORDER BY City, rnk
    """)

    run(conn, "Affordability ranking", """
        SELECT City,
               ROUND(AvgRent, 2) AS LatestRent,
               MedianHouseholdIncome,
               ROUND(AffordabilityIndex, 1) AS AffordabilityIndex,
               RANK() OVER (ORDER BY AffordabilityIndex ASC) AS AffordabilityRank
        FROM affordability
        ORDER BY AffordabilityIndex ASC
    """)

    run(conn, "Vacancy trend 2020-2024", """
        SELECT City, Year, VacancyRate,
               ROUND(VacancyRate - LAG(VacancyRate) OVER (
                   PARTITION BY City ORDER BY Year
               ), 1) AS YoY_change
        FROM vacancy
        ORDER BY City, Year
    """)

    conn.close()
    print("\nDone.")
