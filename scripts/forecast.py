"""
Step 3: Rent forecasting.
Primary model: Meta Prophet (trend + weekly/yearly seasonality + uncertainty intervals).
Fallback:      scikit-learn LinearRegression + sin/cos seasonality (if Prophet unavailable).

Outputs rent_forecast.csv with columns:
  City, date, ForecastRent, Lower80, Upper80, Lower95, Upper95, Type, Model
"""

import os
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

BASE = os.path.join(os.path.dirname(__file__), "..")
CLEAN_DIR = os.path.join(BASE, "data", "cleaned")
FORECAST_PATH = os.path.join(CLEAN_DIR, "rent_forecast.csv")

FORECAST_MONTHS = 12

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score


# ── Prophet model ──────────────────────────────────────────────────────────────

def forecast_city_prophet(df_city):
    """Fit a Prophet model and return a 12-month forecast with uncertainty bands."""
    prophet_df = df_city[["date", "AvgRent"]].rename(columns={"date": "ds", "AvgRent": "y"})

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.80,
        changepoint_prior_scale=0.05,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(prophet_df)

    future = model.make_future_dataframe(periods=FORECAST_MONTHS, freq="MS")
    forecast = model.predict(future)

    # In-sample metrics
    in_sample = forecast[forecast["ds"].isin(prophet_df["ds"])]
    mae = mean_absolute_error(prophet_df["y"], in_sample["yhat"])
    r2 = r2_score(prophet_df["y"], in_sample["yhat"])

    future_only = forecast[~forecast["ds"].isin(prophet_df["ds"])].copy()
    result = pd.DataFrame({
        "City": df_city["City"].iloc[0],
        "date": future_only["ds"].values,
        "ForecastRent": np.round(future_only["yhat"].values, 2),
        "Lower80": np.round(future_only["yhat_lower"].values, 2),
        "Upper80": np.round(future_only["yhat_upper"].values, 2),
        # Prophet's default interval_width=0.80; approximate 95% by scaling
        "Lower95": np.round(future_only["yhat_lower"].values - 0.5 * (future_only["yhat"].values - future_only["yhat_lower"].values), 2),
        "Upper95": np.round(future_only["yhat_upper"].values + 0.5 * (future_only["yhat_upper"].values - future_only["yhat"].values), 2),
        "Type": "Forecast",
        "Model": "Prophet",
    })
    return result, mae, r2


# ── Linear Regression fallback ─────────────────────────────────────────────────

def build_features(df):
    df = df.copy()
    df["t"] = (df["date"] - df["date"].min()).dt.days / 30.0
    df["month"] = df["date"].dt.month
    df["sin_month"] = np.sin(2 * np.pi * df["month"] / 12)
    df["cos_month"] = np.cos(2 * np.pi * df["month"] / 12)
    return df


FEATURE_COLS = ["t", "sin_month", "cos_month"]


def forecast_city_linear(df_city):
    df_city = build_features(df_city).dropna(subset=["AvgRent"])
    X = df_city[FEATURE_COLS].values
    y = df_city["AvgRent"].values

    model = LinearRegression()
    model.fit(X, y)
    y_pred = model.predict(X)
    mae = mean_absolute_error(y, y_pred)
    r2 = r2_score(y, y_pred)
    residual_std = np.std(y - y_pred)

    last_date = df_city["date"].max()
    future_dates = pd.date_range(
        start=last_date + pd.DateOffset(months=1),
        periods=FORECAST_MONTHS, freq="MS",
    )
    t_last = df_city["t"].max()
    t_future = t_last + np.arange(1, FORECAST_MONTHS + 1)
    sin_f = np.sin(2 * np.pi * future_dates.month / 12)
    cos_f = np.cos(2 * np.pi * future_dates.month / 12)
    X_future = np.column_stack([t_future, sin_f, cos_f])
    y_future = model.predict(X_future)

    result = pd.DataFrame({
        "City": df_city["City"].iloc[0],
        "date": future_dates,
        "ForecastRent": np.round(y_future, 2),
        "Lower80": np.round(y_future - 1.28 * residual_std, 2),
        "Upper80": np.round(y_future + 1.28 * residual_std, 2),
        "Lower95": np.round(y_future - 1.96 * residual_std, 2),
        "Upper95": np.round(y_future + 1.96 * residual_std, 2),
        "Type": "Forecast",
        "Model": "LinearRegression",
    })
    return result, mae, r2


# ── Public interface ───────────────────────────────────────────────────────────

def forecast_city(df_city):
    """Fit the best available model for one city."""
    if PROPHET_AVAILABLE:
        return forecast_city_prophet(df_city)
    return forecast_city_linear(df_city)


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    rent_path = os.path.join(CLEAN_DIR, "rents_clean.csv")
    if not os.path.exists(rent_path):
        raise FileNotFoundError(
            f"rents_clean.csv not found at {rent_path}\n"
            "Run scripts/clean_data.py first."
        )

    rents = pd.read_csv(rent_path, parse_dates=["date"])
    model_name = "Prophet" if PROPHET_AVAILABLE else "LinearRegression (Prophet not installed)"
    print(f"Forecasting with: {model_name}")

    all_forecasts = []
    for city, grp in rents.groupby("City"):
        fc, mae, r2 = forecast_city(grp)
        all_forecasts.append(fc)
        print(f"  {city:<20}  MAE=${mae:,.0f}   R²={r2:.3f}")

    forecast_df = pd.concat(all_forecasts, ignore_index=True)
    forecast_df.to_csv(FORECAST_PATH, index=False)
    print(f"\nSaved {len(forecast_df)} rows → {FORECAST_PATH}")

    city1 = forecast_df["City"].iloc[0]
    print(f"\n12-month forecast ({city1}):")
    print(
        forecast_df[forecast_df["City"] == city1][
            ["City", "date", "ForecastRent", "Lower80", "Upper80"]
        ].to_string(index=False)
    )
