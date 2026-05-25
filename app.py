"""
Step 4: Interactive Streamlit web dashboard.
Deploy free on Streamlit Cloud for a shareable live URL.

Local dev:
    streamlit run app.py
"""

import os
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE = os.path.dirname(os.path.abspath(__file__))
CLEAN = os.path.join(BASE, "data", "cleaned")

# Make sure scripts/ is importable
sys.path.insert(0, os.path.join(BASE, "scripts"))


def _bootstrap_data():
    """Auto-generate cleaned data and forecast if not present (e.g. Streamlit Cloud)."""
    os.makedirs(CLEAN, exist_ok=True)
    rents_path = os.path.join(CLEAN, "rents_clean.csv")
    if not os.path.exists(rents_path):
        from clean_data import (
            generate_synthetic_rent, generate_synthetic_vacancy,
            generate_synthetic_income, compute_mom_yoy, compute_affordability,
        )
        rents = compute_mom_yoy(generate_synthetic_rent())
        vacancy = generate_synthetic_vacancy()
        income = generate_synthetic_income()
        afford = compute_affordability(rents, income)
        rents.to_csv(os.path.join(CLEAN, "rents_clean.csv"), index=False)
        vacancy.to_csv(os.path.join(CLEAN, "vacancy_clean.csv"), index=False)
        income.to_csv(os.path.join(CLEAN, "income_clean.csv"), index=False)
        afford.to_csv(os.path.join(CLEAN, "affordability_clean.csv"), index=False)

    forecast_path = os.path.join(CLEAN, "rent_forecast.csv")
    if not os.path.exists(forecast_path):
        from forecast import forecast_city
        import pandas as _pd, numpy as _np
        rents = _pd.read_csv(os.path.join(CLEAN, "rents_clean.csv"), parse_dates=["date"])
        frames = [forecast_city(grp)[0] for _, grp in rents.groupby("City")]
        _pd.concat(frames, ignore_index=True).to_csv(forecast_path, index=False)


_bootstrap_data()

CITY_COLORS = {
    "New York City": "#2E5299",
    "Washington DC": "#C8102E",
    "Maryland Suburbs": "#228B22",
}


def hex_rgba(hex_color, alpha=1.0):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


@st.cache_data
def load_data():
    rents = pd.read_csv(os.path.join(CLEAN, "rents_clean.csv"), parse_dates=["date"])
    vacancy = pd.read_csv(os.path.join(CLEAN, "vacancy_clean.csv"))
    income = pd.read_csv(os.path.join(CLEAN, "income_clean.csv"))
    afford = pd.read_csv(os.path.join(CLEAN, "affordability_clean.csv"))
    forecast_path = os.path.join(CLEAN, "rent_forecast.csv")
    forecast = (
        pd.read_csv(forecast_path, parse_dates=["date"])
        if os.path.exists(forecast_path)
        else pd.DataFrame()
    )
    return rents, vacancy, income, afford, forecast


def callout(text, icon="💡"):
    """Render a styled insight box."""
    st.markdown(
        f"""
        <div style="background:#f0f4ff; border-left:4px solid #2E5299;
                    padding:12px 16px; border-radius:4px; margin:8px 0 16px 0;
                    font-size:0.9rem; color:#1a1a2e; line-height:1.6;">
            {icon} {text}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Real Estate Market Dashboard",
    page_icon="🏙️",
    layout="wide",
)

st.markdown(
    """
    <style>
        .block-container { padding-top: 1.5rem; }
        h1 { color: #2E5299; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── load ───────────────────────────────────────────────────────────────────────
rents, vacancy, income, afford, forecast = load_data()

# ── header ─────────────────────────────────────────────────────────────────────
st.title("🏙️ Multifamily Real Estate Market Dashboard")
st.caption(
    "New York City · Washington DC · Maryland Suburbs  |  "
    "Data: Zillow Research, HUD, US Census Bureau"
)

# ── sidebar ────────────────────────────────────────────────────────────────────
ALL_CITIES = ["New York City", "Washington DC", "Maryland Suburbs"]

st.sidebar.header("Filters")

view_mode = st.sidebar.radio(
    "View Mode",
    ["All Markets", "Compare Two Cities"],
    help="Switch between full overview and focused head-to-head comparison",
)

if view_mode == "Compare Two Cities":
    city_a = st.sidebar.selectbox("Market A", ALL_CITIES, index=0)
    city_b = st.sidebar.selectbox(
        "Market B", [c for c in ALL_CITIES if c != city_a], index=0
    )
    cities = [city_a, city_b]
    st.sidebar.info("Showing focused head-to-head comparison. Switch to **All Markets** to see all three.")
else:
    cities = st.sidebar.multiselect(
        "Markets",
        options=ALL_CITIES,
        default=ALL_CITIES,
    )

date_min = rents["date"].min().date()
date_max = rents["date"].max().date()
date_range = st.sidebar.date_input(
    "Date Range",
    value=(date_min, date_max),
    min_value=date_min,
    max_value=date_max,
)

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_dt, end_dt = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
else:
    start_dt, end_dt = pd.Timestamp(date_min), pd.Timestamp(date_max)

filtered = rents[
    rents["City"].isin(cities)
    & (rents["date"] >= start_dt)
    & (rents["date"] <= end_dt)
]

# ── KPI cards ──────────────────────────────────────────────────────────────────
st.subheader("Market Snapshot")
latest = filtered.groupby("City").last().reset_index()
kpi_cols = st.columns(len(cities) if cities else 1)

for i, city in enumerate(cities):
    row = latest[latest["City"] == city]
    if row.empty:
        continue
    rent = row["AvgRent"].values[0]
    yoy = row["YoYChange"].values[0] if "YoYChange" in row.columns else None
    with kpi_cols[i]:
        st.metric(
            label=city,
            value=f"${rent:,.0f}/mo",
            delta=f"{yoy:+.1f}% YoY" if yoy is not None and not pd.isna(yoy) else "—",
        )

# KPI summary sentence
if not latest.empty and len(cities) > 0:
    top = latest.loc[latest["AvgRent"].idxmax()]
    low = latest.loc[latest["AvgRent"].idxmin()]
    best_growth = latest.loc[latest["YoYChange"].idxmax()] if "YoYChange" in latest.columns else None
    gap = top["AvgRent"] - low["AvgRent"]
    summary_parts = [
        f"**{top['City']}** commands the highest rents at **${top['AvgRent']:,.0f}/mo**, "
        f"${gap:,.0f} more per month than **{low['City']}** (${low['AvgRent']:,.0f}/mo)."
    ]
    if best_growth is not None and not pd.isna(best_growth["YoYChange"]):
        summary_parts.append(
            f" Year-over-year, **{best_growth['City']}** is growing fastest at "
            f"**{best_growth['YoYChange']:+.1f}%**."
        )
    callout(" ".join(summary_parts), icon="📌")

st.divider()

# ── tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(
    ["📈 Rent Trends", "🏗️ Market Comparison", "🔮 Forecast", "📊 Raw Data"]
)

# ── Tab 1: Rent Trends ─────────────────────────────────────────────────────────
with tab1:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Average Rent Over Time")
        fig = px.line(
            filtered,
            x="date", y="AvgRent",
            color="City",
            color_discrete_map=CITY_COLORS,
            labels={"AvgRent": "Avg Rent ($)", "date": ""},
        )
        fig.update_layout(legend_title_text="", height=350)

        # Annotate the COVID-19 correction if the date range covers it
        if start_dt <= pd.Timestamp("2020-06-01") and end_dt >= pd.Timestamp("2021-06-01"):
            fig.add_vrect(
                x0="2020-04-01", x1="2021-06-01",
                fillcolor="rgba(200,16,46,0.07)",
                layer="below", line_width=0,
                annotation_text="COVID-19<br>correction",
                annotation_position="top left",
                annotation_font_size=10,
                annotation_font_color="#C8102E",
            )
            nyc_covid = filtered[
                (filtered["City"] == "New York City")
                & (filtered["date"] >= "2020-04-01")
                & (filtered["date"] <= "2021-06-01")
            ]
            if not nyc_covid.empty:
                trough = nyc_covid.loc[nyc_covid["AvgRent"].idxmin()]
                fig.add_annotation(
                    x=trough["date"], y=trough["AvgRent"],
                    text=f"NYC trough<br>${trough['AvgRent']:,.0f}",
                    showarrow=True, arrowhead=2,
                    arrowcolor="#2E5299",
                    font=dict(size=10, color="#2E5299"),
                    ax=50, ay=-45,
                )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### Year-over-Year Rent Growth (%)")
        yoy_df = filtered.dropna(subset=["YoYChange"])
        fig2 = px.line(
            yoy_df,
            x="date", y="YoYChange",
            color="City",
            color_discrete_map=CITY_COLORS,
            labels={"YoYChange": "YoY Change (%)", "date": ""},
        )
        fig2.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig2.update_layout(legend_title_text="", height=350)
        st.plotly_chart(fig2, use_container_width=True)

    # Dynamic summary for rent trend charts
    if not latest.empty and "YoYChange" in latest.columns:
        city_summaries = []
        for _, row in latest[latest["City"].isin(cities)].iterrows():
            yoy = row["YoYChange"]
            direction = "up" if yoy > 0 else "down"
            city_summaries.append(f"{row['City']} is {direction} {abs(yoy):.1f}% from a year ago (${row['AvgRent']:,.0f}/mo)")
        callout(
            "<b>How to read these charts:</b> The left chart shows the dollar rent level for each city "
            "since 2019 — a rising line means rents are going up. The right chart shows the percentage "
            "change compared to the same month one year ago, so it reflects the pace of change, not the "
            f"absolute level. Currently: {'; '.join(city_summaries)}.",
            icon="📖"
        )

    st.markdown("##### Month-over-Month Change (%)")
    mom_df = filtered.dropna(subset=["MoMChange"])
    recent_mom = mom_df[mom_df["date"] >= mom_df["date"].max() - pd.DateOffset(months=24)]
    fig3 = px.bar(
        recent_mom,
        x="date", y="MoMChange",
        color="City",
        barmode="group",
        color_discrete_map=CITY_COLORS,
        labels={"MoMChange": "MoM Change (%)", "date": ""},
    )
    fig3.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig3.update_layout(legend_title_text="", height=300)
    st.plotly_chart(fig3, use_container_width=True)

    # MoM summary
    if not recent_mom.empty:
        last_3 = mom_df.groupby("City").tail(3).groupby("City")["MoMChange"].mean()
        trending_up = [c for c in cities if c in last_3.index and last_3[c] > 0]
        trending_down = [c for c in cities if c in last_3.index and last_3[c] <= 0]
        mom_parts = ["<b>Month-over-Month</b> measures the change from one month to the next — bars above zero mean rents rose that month, bars below zero mean they fell."]
        if trending_up:
            mom_parts.append(f" Over the past 3 months, <b>{'</b> and <b>'.join(trending_up)}</b> show consistent upward momentum.")
        if trending_down:
            mom_parts.append(f" <b>{'</b> and <b>'.join(trending_down)}</b> have seen slight softening recently.")
        callout(" ".join(mom_parts), icon="📖")

# ── Tab 2: Market Comparison ───────────────────────────────────────────────────
with tab2:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Latest Average Rent by Market")
        bar_df = latest[latest["City"].isin(cities)].sort_values("AvgRent", ascending=False)
        fig4 = px.bar(
            bar_df,
            x="City", y="AvgRent",
            color="City",
            color_discrete_map=CITY_COLORS,
            text_auto="$,.0f",
            labels={"AvgRent": "Avg Rent ($)"},
        )
        fig4.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig4, use_container_width=True)

    with col2:
        st.markdown("##### Affordability Index (% of income spent on rent)")
        aff = afford[afford["City"].isin(cities)].copy()
        fig5 = px.bar(
            aff,
            x="City", y="AffordabilityIndex",
            color="City",
            color_discrete_map=CITY_COLORS,
            text_auto=".1f",
            labels={"AffordabilityIndex": "% of Annual Income"},
        )
        fig5.add_hline(
            y=30, line_dash="dash", line_color="orange",
            annotation_text="30% affordability threshold",
            annotation_position="top right"
        )
        fig5.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig5, use_container_width=True)

    # Affordability summary
    aff_filtered = aff[aff["City"].isin(cities)].sort_values("AffordabilityIndex")
    if not aff_filtered.empty:
        most_afford = aff_filtered.iloc[0]
        least_afford = aff_filtered.iloc[-1]
        under_30 = aff_filtered[aff_filtered["AffordabilityIndex"] < 30]
        over_30 = aff_filtered[aff_filtered["AffordabilityIndex"] >= 30]
        afford_text = (
            "<b>Affordability Index</b> = (monthly rent × 12) ÷ median household income. "
            "Housing economists consider anything above 30% a cost burden — meaning a household "
            f"spends more than a third of income on rent. "
        )
        if not under_30.empty:
            afford_text += f"<b>{', '.join(under_30['City'].tolist())}</b> fall below the threshold, making {'it' if len(under_30)==1 else 'them'} the most accessible {'market' if len(under_30)==1 else 'markets'}. "
        if not over_30.empty:
            afford_text += f"<b>{', '.join(over_30['City'].tolist())}</b> exceed 30%, indicating significant rent burden for median-income households."
        callout(afford_text, icon="📖")

    st.markdown("##### Vacancy Rate Trend (2020–2024)")
    vac = vacancy[vacancy["City"].isin(cities)]
    fig6 = px.line(
        vac,
        x="Year", y="VacancyRate",
        color="City",
        markers=True,
        color_discrete_map=CITY_COLORS,
        labels={"VacancyRate": "Vacancy Rate (%)"},
    )
    fig6.add_hrect(y0=0, y1=5, fillcolor="green", opacity=0.05,
                   annotation_text="Landlord-favorable (<5%)", annotation_position="top left")
    fig6.update_layout(legend_title_text="", height=300)
    st.plotly_chart(fig6, use_container_width=True)

    # Vacancy summary
    if not vac.empty:
        latest_vac = vac[vac["Year"] == vac["Year"].max()]
        all_under_5 = (latest_vac["VacancyRate"] < 5).all()
        lowest_vac = latest_vac.loc[latest_vac["VacancyRate"].idxmin()]
        vac_text = (
            "<b>Vacancy rate</b> is the percentage of rental units sitting empty. "
            "A low vacancy rate means high demand — landlords have pricing power and "
            "tenants have fewer options. Economists generally consider below 5% a landlord-favorable market. "
        )
        if all_under_5:
            vac_text += f"All three markets are currently below 5%, a strong signal of sustained rental demand. "
        vac_text += (
            f"<b>{lowest_vac['City']}</b> has the tightest market at just "
            f"<b>{lowest_vac['VacancyRate']}%</b> vacancy as of {int(latest_vac['Year'].max())}."
        )
        callout(vac_text, icon="📖")

    # ── Vacancy vs Rent Growth scatter ────────────────────────────────────────
    st.markdown("##### Vacancy Rate vs. Rent Growth — Is Low Vacancy Driving Higher Rents?")

    # Build annual YoY average per city from the full (unfiltered) rent data
    rent_annual = (
        rents.dropna(subset=["YoYChange"])
        .assign(Year=lambda d: d["date"].dt.year)
        .groupby(["City", "Year"])["YoYChange"]
        .mean()
        .reset_index()
        .rename(columns={"YoYChange": "AvgYoYChange"})
    )
    scatter_df = vacancy.merge(rent_annual, on=["City", "Year"])
    scatter_df = scatter_df[scatter_df["City"].isin(cities)]

    if not scatter_df.empty:
        fig_scatter = px.scatter(
            scatter_df,
            x="VacancyRate",
            y="AvgYoYChange",
            color="City",
            size_max=14,
            symbol="City",
            text="Year",
            trendline="ols",
            color_discrete_map=CITY_COLORS,
            labels={
                "VacancyRate": "Vacancy Rate (%)",
                "AvgYoYChange": "Avg YoY Rent Growth (%)",
            },
        )
        fig_scatter.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.4)
        fig_scatter.update_traces(textposition="top center", textfont_size=9)
        fig_scatter.update_layout(height=380, legend_title_text="")
        st.plotly_chart(fig_scatter, use_container_width=True)

        # Compute overall correlation for the callout
        corr = scatter_df["VacancyRate"].corr(scatter_df["AvgYoYChange"])
        direction = "negative" if corr < 0 else "positive"
        strength = "strong" if abs(corr) > 0.6 else "moderate" if abs(corr) > 0.3 else "weak"
        callout(
            f"<b>How to read this chart:</b> Each dot is one city in one year. "
            f"The x-axis is how many units were sitting empty that year; the y-axis is how fast rents grew. "
            f"The trend line shows the overall relationship. "
            f"Here the correlation is <b>{strength} and {direction}</b> (r = {corr:.2f}) — "
            + (
                "meaning tighter markets (lower vacancy) do tend to see faster rent growth, "
                "supporting the landlord-favorable thesis."
                if corr < -0.2 else
                "meaning vacancy alone is not the dominant driver of rent growth across these markets."
            ),
            icon="📖"
        )

    # ── Head-to-Head comparison (only visible in Compare Two Cities mode) ──────
    if view_mode == "Compare Two Cities" and len(cities) == 2:
        st.divider()
        a, b = cities[0], cities[1]
        st.markdown(f"### 🔍 Head-to-Head: {a} vs. {b}")

        a_row = latest[latest["City"] == a]
        b_row = latest[latest["City"] == b]
        a_aff = afford[afford["City"] == a]
        b_aff = afford[afford["City"] == b]
        a_vac = vacancy[(vacancy["City"] == a) & (vacancy["Year"] == vacancy["Year"].max())]
        b_vac = vacancy[(vacancy["City"] == b) & (vacancy["Year"] == vacancy["Year"].max())]

        metrics = [
            ("Latest Avg Rent", f"${a_row['AvgRent'].values[0]:,.0f}/mo" if not a_row.empty else "—",
             f"${b_row['AvgRent'].values[0]:,.0f}/mo" if not b_row.empty else "—"),
            ("YoY Rent Growth", f"{a_row['YoYChange'].values[0]:+.1f}%" if not a_row.empty else "—",
             f"{b_row['YoYChange'].values[0]:+.1f}%" if not b_row.empty else "—"),
            ("Affordability Index", f"{a_aff['AffordabilityIndex'].values[0]:.1f}%" if not a_aff.empty else "—",
             f"{b_aff['AffordabilityIndex'].values[0]:.1f}%" if not b_aff.empty else "—"),
            ("Median Household Income", f"${a_aff['MedianHouseholdIncome'].values[0]:,.0f}" if not a_aff.empty else "—",
             f"${b_aff['MedianHouseholdIncome'].values[0]:,.0f}" if not b_aff.empty else "—"),
            ("Vacancy Rate (2024)", f"{a_vac['VacancyRate'].values[0]}%" if not a_vac.empty else "—",
             f"{b_vac['VacancyRate'].values[0]}%" if not b_vac.empty else "—"),
        ]

        hdr_col, a_col, b_col = st.columns([2, 1, 1])
        hdr_col.markdown(f"**Metric**")
        a_col.markdown(f"**{a}**")
        b_col.markdown(f"**{b}**")
        st.markdown("---")
        for label, val_a, val_b in metrics:
            hdr_col, a_col, b_col = st.columns([2, 1, 1])
            hdr_col.write(label)
            a_col.write(val_a)
            b_col.write(val_b)

        # Narrative verdict
        if not a_row.empty and not b_row.empty:
            cheaper = a if a_row["AvgRent"].values[0] < b_row["AvgRent"].values[0] else b
            faster_growth = a if a_row["YoYChange"].values[0] > b_row["YoYChange"].values[0] else b
            more_afford = a if (not a_aff.empty and not b_aff.empty and
                                a_aff["AffordabilityIndex"].values[0] < b_aff["AffordabilityIndex"].values[0]) else b
            callout(
                f"<b>Verdict:</b> <b>{cheaper}</b> is the lower-cost market on absolute rent. "
                f"<b>{faster_growth}</b> is growing faster year-over-year, suggesting stronger near-term demand. "
                f"<b>{more_afford}</b> offers the better rent-to-income ratio, making it more accessible "
                f"to the local workforce and less exposed to affordability-driven tenant turnover.",
                icon="⚖️"
            )

# ── Tab 3: Forecast ────────────────────────────────────────────────────────────
with tab3:
    if forecast.empty:
        st.info(
            "No forecast data found. Run `python scripts/forecast.py` to generate "
            "`data/cleaned/rent_forecast.csv`, then restart the app."
        )
    else:
        st.markdown("##### 12-Month Rent Forecast (Linear Regression + Seasonality)")

        fc_cities = [c for c in cities if c in forecast["City"].unique()]
        hist_tail = filtered[filtered["date"] >= filtered["date"].max() - pd.DateOffset(months=24)]

        fig7 = go.Figure()
        for city in fc_cities:
            color = CITY_COLORS.get(city, "#888888")
            h = hist_tail[hist_tail["City"] == city].sort_values("date")
            f = forecast[forecast["City"] == city].sort_values("date")

            fig7.add_trace(go.Scatter(
                x=h["date"], y=h["AvgRent"],
                mode="lines",
                name=f"{city} (actual)",
                line=dict(color=color, width=2.5),
            ))

            # Prepend the last actual point so the forecast line starts
            # exactly where the historical line ends — no visual gap
            last_actual = h.iloc[[-1]][["date", "AvgRent"]].rename(columns={"AvgRent": "ForecastRent"})
            f_connected = pd.concat(
                [last_actual, f[["date", "ForecastRent"]]], ignore_index=True
            )
            fig7.add_trace(go.Scatter(
                x=f_connected["date"], y=f_connected["ForecastRent"],
                mode="lines",
                name=f"{city} (forecast)",
                line=dict(color=color, width=2.5, dash="dot"),
            ))

            # 80% confidence band (shaded area between lower and upper)
            if "Lower80" in f.columns and "Upper80" in f.columns:
                upper = pd.concat([
                    h.iloc[[-1]][["date"]].assign(Upper80=h.iloc[-1]["AvgRent"]),
                    f[["date", "Upper80"]]
                ], ignore_index=True)
                lower = pd.concat([
                    h.iloc[[-1]][["date"]].assign(Lower80=h.iloc[-1]["AvgRent"]),
                    f[["date", "Lower80"]]
                ], ignore_index=True)
                fig7.add_trace(go.Scatter(
                    x=pd.concat([upper["date"], lower["date"][::-1]]),
                    y=pd.concat([upper["Upper80"], lower["Lower80"][::-1]]),
                    fill="toself",
                    fillcolor=hex_rgba(color, 0.12),
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo="skip",
                    name=f"{city} 80% CI",
                ))

        # Add a vertical "today" marker
        cutoff = hist_tail["date"].max()
        fig7.add_vline(
            x=cutoff.timestamp() * 1000,
            line_dash="dash", line_color="gray", opacity=0.6,
            annotation_text="Forecast start", annotation_position="top right"
        )

        fig7.update_layout(
            height=440,
            legend_title_text="",
            xaxis_title="",
            yaxis_title="Avg Rent ($)",
            hovermode="x unified",
        )
        st.plotly_chart(fig7, use_container_width=True)

        # Forecast summary
        if fc_cities:
            end_rents = forecast[forecast["City"].isin(fc_cities)].groupby("City")["ForecastRent"].last()
            start_rents = {
                city: latest[latest["City"] == city]["AvgRent"].values[0]
                for city in fc_cities
                if not latest[latest["City"] == city].empty
            }
            fc_lines = []
            for city in fc_cities:
                if city in start_rents and city in end_rents.index:
                    change = end_rents[city] - start_rents[city]
                    pct = (change / start_rents[city]) * 100
                    direction = "increase" if change > 0 else "decrease"
                    fc_lines.append(
                        f"<b>{city}</b>: projected to {direction} from "
                        f"${start_rents[city]:,.0f} → ${end_rents[city]:,.0f} "
                        f"({pct:+.1f}% over 12 months)"
                    )

            callout(
                "<b>How to read this chart:</b> The solid lines show actual historical rents. "
                "The dotted lines show where the model projects rents are heading over the next 12 months "
                "based on the historical trend and seasonal patterns (rents typically rise in summer, "
                "soften in winter). This is a directional estimate, not a guarantee. "
                + ("<br>" + "<br>".join(fc_lines) if fc_lines else ""),
                icon="📖"
            )

            callout(
                "⚠️ <b>Model note:</b> This forecast uses linear regression — it captures the overall "
                "trend and seasonal rhythm well, but will not anticipate sudden economic shocks "
                "(recessions, policy changes, major job market shifts). Use it as a baseline, "
                "not a certainty.",
                icon="⚠️"
            )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Projected rents — next 12 months**")
            fc_table = forecast[forecast["City"].isin(fc_cities)][
                ["City", "date", "ForecastRent"]
            ].copy()
            fc_table["date"] = fc_table["date"].dt.strftime("%b %Y")
            fc_table["ForecastRent"] = fc_table["ForecastRent"].map("${:,.0f}".format)
            fc_table.columns = ["Market", "Month", "Projected Rent"]
            st.dataframe(fc_table, use_container_width=True, hide_index=True)

# ── Tab 4: Raw Data ────────────────────────────────────────────────────────────
with tab4:
    st.markdown("##### Rent Data")
    show = filtered[["City", "date", "AvgRent", "MoMChange", "YoYChange"]].copy()
    show["date"] = show["date"].dt.strftime("%Y-%m")
    show["AvgRent"] = show["AvgRent"].map("${:,.0f}".format)
    show["MoMChange"] = show["MoMChange"].map(lambda x: f"{x:+.2f}%" if pd.notna(x) else "—")
    show["YoYChange"] = show["YoYChange"].map(lambda x: f"{x:+.2f}%" if pd.notna(x) else "—")
    show.columns = ["Market", "Month", "Avg Rent", "MoM Change", "YoY Change"]
    st.dataframe(
        show.sort_values(["Market", "Month"], ascending=[True, False]),
        use_container_width=True, hide_index=True
    )

    csv_export = filtered[["City", "date", "AvgRent", "MoMChange", "YoYChange"]].copy()
    csv_export["date"] = csv_export["date"].dt.strftime("%Y-%m")
    csv_export.columns = ["Market", "Month", "Avg Rent", "MoM Change (%)", "YoY Change (%)"]
    st.download_button(
        label="⬇️ Download filtered rent data as CSV",
        data=csv_export.to_csv(index=False),
        file_name="real_estate_rents_filtered.csv",
        mime="text/csv",
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Vacancy Rates by Year")
        st.dataframe(vacancy[vacancy["City"].isin(cities)], use_container_width=True, hide_index=True)
    with col2:
        st.markdown("##### Affordability Index")
        st.dataframe(afford[afford["City"].isin(cities)], use_container_width=True, hide_index=True)

# ── footer ─────────────────────────────────────────────────────────────────────
st.divider()
with st.expander("ℹ️ About this dashboard"):
    st.markdown("""
    **Data sources**
    - Rent index: Zillow Observed Rent Index (ZORI) — metro-level monthly averages
    - Home values: Zillow Home Value Index (ZHVI)
    - Fair Market Rents: HUD FMR dataset
    - Income: US Census Bureau American Community Survey (ACS)
    - Vacancy rates: Census/CoStar estimates

    **Methodology**
    - Affordability Index = (monthly rent × 12) ÷ median household income × 100
    - Forecasting model: scikit-learn LinearRegression with time index + sin/cos monthly seasonality features
    - MoM and YoY changes computed from the cleaned rent time series

    **Limitations**
    - Vacancy and income data are point-in-time estimates, not continuous series
    - Forecast is a linear extrapolation and does not model macroeconomic shocks
    - Maryland Suburbs figure represents Rockville/Bethesda/Silver Spring metro
    """)
st.caption("Nicholas Black — Real Estate Market Analysis Portfolio Project")
