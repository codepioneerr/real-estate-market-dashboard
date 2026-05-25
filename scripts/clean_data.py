"""
Cleans raw Zillow CSVs and exports tidy long-format files to data/cleaned/.
Handles both real downloaded data and falls back to synthetic data for demo
if the raw files are not present.
"""

import os
import pandas as pd
import numpy as np

BASE = os.path.join(os.path.dirname(__file__), "..")
RAW_DIR = os.path.join(BASE, "data", "raw")
CLEAN_DIR = os.path.join(BASE, "data", "cleaned")
os.makedirs(CLEAN_DIR, exist_ok=True)

CITIES = {
    "New York, NY": "New York City",
    "Washington, DC": "Washington DC",
    "Rockville, MD": "Maryland Suburbs",
}

# Fallback city match strings for partial matching
CITY_ALIASES = {
    "New York City": ["New York", "New York, NY"],
    "Washington DC": ["Washington", "Washington, DC", "Washington-Arlington"],
    "Maryland Suburbs": ["Rockville", "Baltimore", "Silver Spring", "Bethesda"],
}


def melt_zillow(df, value_name):
    """Convert Zillow wide format (date columns) to long format."""
    id_cols = [c for c in df.columns if not c.startswith("20") and not c.startswith("19")]
    date_cols = [c for c in df.columns if c.startswith("20") or c.startswith("19")]
    melted = df.melt(id_vars=id_cols, value_vars=date_cols, var_name="date", value_name=value_name)
    melted["date"] = pd.to_datetime(melted["date"])
    return melted


def filter_cities(df, region_col="RegionName"):
    rows = []
    for label, aliases in CITY_ALIASES.items():
        mask = df[region_col].astype(str).apply(
            lambda x: any(alias.lower() in x.lower() for alias in aliases)
        )
        matched = df[mask].copy()
        matched["City"] = label
        rows.append(matched)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def load_zori():
    path = os.path.join(RAW_DIR, "zillow_zori_metro.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    df = melt_zillow(df, "AvgRent")
    df = filter_cities(df)
    df = df[["City", "date", "AvgRent"]].dropna()
    df = df.sort_values(["City", "date"])
    return df


def load_zhvi():
    path = os.path.join(RAW_DIR, "zillow_zhvi_metro.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    df = melt_zillow(df, "MedianHomeValue")
    df = filter_cities(df)
    df = df[["City", "date", "MedianHomeValue"]].dropna()
    df = df.sort_values(["City", "date"])
    return df


def generate_synthetic_rent():
    """Realistic synthetic rent data based on published 2020-2024 market data."""
    np.random.seed(42)
    months = pd.date_range("2019-01", "2024-12", freq="MS")
    records = []

    baselines = {
        "New York City": 3200,
        "Washington DC": 2100,
        "Maryland Suburbs": 1850,
    }
    trends = {
        "New York City": 0.004,
        "Washington DC": 0.005,
        "Maryland Suburbs": 0.004,
    }
    # COVID dip: NYC dropped ~10% mid-2020, recovered by 2022
    covid_dip = {
        "New York City": ("2020-04", "2021-06", -0.10),
        "Washington DC": ("2020-04", "2021-03", -0.03),
        "Maryland Suburbs": ("2020-04", "2021-01", -0.02),
    }

    for city, base in baselines.items():
        rent = base
        dip_start, dip_end, dip_pct = covid_dip[city]
        for m in months:
            noise = np.random.normal(0, 20)
            in_dip = pd.Timestamp(dip_start) <= m <= pd.Timestamp(dip_end)
            adj = dip_pct / 15 if in_dip else 0
            rent = rent * (1 + trends[city] + adj) + noise
            records.append({"City": city, "date": m, "AvgRent": round(rent, 2)})

    return pd.DataFrame(records)


def generate_synthetic_vacancy():
    """Synthetic vacancy rate data (%) by city and year."""
    data = {
        "City": ["New York City"] * 5 + ["Washington DC"] * 5 + ["Maryland Suburbs"] * 5,
        "Year": [2020, 2021, 2022, 2023, 2024] * 3,
        "VacancyRate": [
            5.8, 6.9, 4.2, 3.1, 2.8,   # NYC — spiked during COVID
            6.2, 5.8, 4.9, 4.1, 3.7,   # DC
            5.1, 5.3, 4.0, 3.5, 3.2,   # Maryland
        ],
    }
    return pd.DataFrame(data)


def generate_synthetic_income():
    """Median household income by city (Census ACS estimates)."""
    data = {
        "City": ["New York City", "Washington DC", "Maryland Suburbs"],
        "MedianHouseholdIncome": [70700, 93600, 110200],
    }
    return pd.DataFrame(data)


def compute_mom_yoy(df):
    df = df.sort_values(["City", "date"]).copy()
    df["MoMChange"] = df.groupby("City")["AvgRent"].pct_change() * 100
    df["YoYChange"] = df.groupby("City")["AvgRent"].pct_change(12) * 100
    return df


def compute_affordability(rent_df, income_df):
    latest = rent_df.groupby("City")["AvgRent"].last().reset_index()
    merged = latest.merge(income_df, on="City")
    # Rent-to-income ratio: (monthly rent * 12) / annual income
    merged["AffordabilityIndex"] = (merged["AvgRent"] * 12 / merged["MedianHouseholdIncome"]) * 100
    return merged


if __name__ == "__main__":
    print("Loading rent data...")
    rent_df = load_zori()
    if rent_df is None or rent_df.empty:
        print("  No Zillow ZORI file found — using synthetic data")
        print("  (Run scripts/fetch_data.py to download real Zillow data)")
        rent_df = generate_synthetic_rent()
    else:
        print(f"  Loaded {len(rent_df)} rent records from Zillow")

    rent_df = compute_mom_yoy(rent_df)
    rent_df.to_csv(os.path.join(CLEAN_DIR, "rents_clean.csv"), index=False)
    print(f"  Saved rents_clean.csv ({len(rent_df)} rows)")

    print("Loading home value data...")
    zhvi_df = load_zhvi()
    if zhvi_df is None or zhvi_df.empty:
        print("  No Zillow ZHVI file found — skipping home values")
        zhvi_df = pd.DataFrame()
    else:
        zhvi_df.to_csv(os.path.join(CLEAN_DIR, "home_values_clean.csv"), index=False)
        print(f"  Saved home_values_clean.csv ({len(zhvi_df)} rows)")

    print("Generating vacancy and income data...")
    vacancy_df = generate_synthetic_vacancy()
    income_df = generate_synthetic_income()
    vacancy_df.to_csv(os.path.join(CLEAN_DIR, "vacancy_clean.csv"), index=False)
    income_df.to_csv(os.path.join(CLEAN_DIR, "income_clean.csv"), index=False)

    afford_df = compute_affordability(rent_df, income_df)
    afford_df.to_csv(os.path.join(CLEAN_DIR, "affordability_clean.csv"), index=False)
    print("  Saved vacancy_clean.csv, income_clean.csv, affordability_clean.csv")

    print("\nDone. Run scripts/build_dashboard.py to generate the Excel dashboard.")
