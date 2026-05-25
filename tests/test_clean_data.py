"""
Unit tests for scripts/clean_data.py — data cleaning and transformation logic.
Run with: pytest tests/
"""

import sys
import os
import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from clean_data import (
    melt_zillow,
    filter_cities,
    generate_synthetic_rent,
    generate_synthetic_vacancy,
    generate_synthetic_income,
    compute_mom_yoy,
    compute_affordability,
)


# ── melt_zillow ────────────────────────────────────────────────────────────────

def test_melt_zillow_produces_long_format():
    df = pd.DataFrame({
        "RegionName": ["City A", "City B"],
        "2023-01": [1000, 2000],
        "2023-02": [1010, 2020],
    })
    result = melt_zillow(df, "AvgRent")
    assert "date" in result.columns
    assert "AvgRent" in result.columns
    assert len(result) == 4  # 2 cities × 2 months


def test_melt_zillow_parses_dates():
    df = pd.DataFrame({"RegionName": ["X"], "2022-06": [1500]})
    result = melt_zillow(df, "AvgRent")
    assert pd.api.types.is_datetime64_any_dtype(result["date"])


# ── filter_cities ──────────────────────────────────────────────────────────────

def test_filter_cities_matches_known_aliases():
    df = pd.DataFrame({
        "RegionName": ["New York, NY", "Washington, DC", "Rockville, MD", "Austin, TX"],
        "value": [1, 2, 3, 4],
    })
    result = filter_cities(df)
    found = set(result["City"].unique())
    assert "New York City" in found
    assert "Washington DC" in found
    assert "Maryland Suburbs" in found
    assert len(result[result["City"] == "New York City"]) == 1


def test_filter_cities_excludes_unrelated():
    df = pd.DataFrame({"RegionName": ["Austin, TX", "Denver, CO"], "value": [1, 2]})
    result = filter_cities(df)
    assert result.empty or not any(c in result.get("City", []) for c in ["New York City", "Washington DC"])


# ── synthetic data ─────────────────────────────────────────────────────────────

def test_synthetic_rent_has_three_cities():
    df = generate_synthetic_rent()
    assert set(df["City"].unique()) == {"New York City", "Washington DC", "Maryland Suburbs"}


def test_synthetic_rent_date_range():
    df = generate_synthetic_rent()
    assert df["date"].min() <= pd.Timestamp("2019-01-01")
    assert df["date"].max() >= pd.Timestamp("2024-01-01")


def test_synthetic_rent_no_nulls():
    df = generate_synthetic_rent()
    assert df["AvgRent"].notna().all()


def test_synthetic_vacancy_shape():
    df = generate_synthetic_vacancy()
    assert len(df) == 15  # 3 cities × 5 years
    assert set(df["City"].unique()) == {"New York City", "Washington DC", "Maryland Suburbs"}


def test_synthetic_vacancy_rates_realistic():
    df = generate_synthetic_vacancy()
    assert (df["VacancyRate"] >= 0).all()
    assert (df["VacancyRate"] <= 15).all()


def test_synthetic_income_three_cities():
    df = generate_synthetic_income()
    assert len(df) == 3
    assert "MedianHouseholdIncome" in df.columns
    assert (df["MedianHouseholdIncome"] > 0).all()


# ── compute_mom_yoy ────────────────────────────────────────────────────────────

def test_compute_mom_yoy_adds_columns():
    df = generate_synthetic_rent()
    result = compute_mom_yoy(df)
    assert "MoMChange" in result.columns
    assert "YoYChange" in result.columns


def test_compute_yoy_is_null_for_first_12_months():
    df = generate_synthetic_rent()
    result = compute_mom_yoy(df)
    nyc = result[result["City"] == "New York City"].sort_values("date")
    assert nyc.iloc[:12]["YoYChange"].isna().all()
    assert nyc.iloc[12]["YoYChange"] is not None


# ── compute_affordability ──────────────────────────────────────────────────────

def test_affordability_index_formula():
    rent_df = pd.DataFrame({
        "City": ["New York City"],
        "date": [pd.Timestamp("2024-12-01")],
        "AvgRent": [3000.0],
    })
    income_df = pd.DataFrame({
        "City": ["New York City"],
        "MedianHouseholdIncome": [72000],
    })
    result = compute_affordability(rent_df, income_df)
    expected = (3000 * 12 / 72000) * 100
    assert abs(result["AffordabilityIndex"].values[0] - expected) < 0.01


def test_affordability_all_cities():
    rent_df = generate_synthetic_rent()
    income_df = generate_synthetic_income()
    result = compute_affordability(rent_df, income_df)
    assert len(result) == 3
    assert (result["AffordabilityIndex"] > 0).all()
