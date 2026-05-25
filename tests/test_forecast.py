"""
Unit tests for scripts/forecast.py — model training and output structure.
Run with: pytest tests/
"""

import sys
import os
import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from clean_data import generate_synthetic_rent, compute_mom_yoy
from forecast import forecast_city, build_features, FORECAST_MONTHS


@pytest.fixture
def nyc_rents():
    df = generate_synthetic_rent()
    return df[df["City"] == "New York City"].copy()


def test_forecast_output_length(nyc_rents):
    fc, _, _ = forecast_city(nyc_rents)
    assert len(fc) == FORECAST_MONTHS


def test_forecast_starts_after_history(nyc_rents):
    fc, _, _ = forecast_city(nyc_rents)
    last_actual = nyc_rents["date"].max()
    assert fc["date"].min() > last_actual


def test_forecast_has_confidence_columns(nyc_rents):
    fc, _, _ = forecast_city(nyc_rents)
    for col in ["ForecastRent", "Lower80", "Upper80", "Lower95", "Upper95", "Model"]:
        assert col in fc.columns, f"Missing column: {col}"


def test_confidence_intervals_ordered(nyc_rents):
    fc, _, _ = forecast_city(nyc_rents)
    assert (fc["Lower95"] <= fc["Lower80"]).all()
    assert (fc["Lower80"] <= fc["ForecastRent"]).all()
    assert (fc["ForecastRent"] <= fc["Upper80"]).all()
    assert (fc["Upper80"] <= fc["Upper95"]).all()


def test_r2_reasonable(nyc_rents):
    _, mae, r2 = forecast_city(nyc_rents)
    assert r2 > 0.0, "R² should be positive for a sensible model"
    assert mae < 500, "MAE should be under $500 for synthetic data"


def test_build_features_adds_columns(nyc_rents):
    result = build_features(nyc_rents)
    assert "t" in result.columns
    assert "sin_month" in result.columns
    assert "cos_month" in result.columns


def test_all_cities_forecast():
    df = generate_synthetic_rent()
    results = []
    for city, grp in df.groupby("City"):
        fc, mae, r2 = forecast_city(grp)
        results.append(fc)
        assert len(fc) == FORECAST_MONTHS
        assert r2 > 0
    combined = pd.concat(results)
    assert combined["City"].nunique() == 3
