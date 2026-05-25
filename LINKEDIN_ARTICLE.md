# LinkedIn Article Draft

**Suggested title:** "I Built a Real Estate Market Intelligence Dashboard From Scratch — Here's What the Data Says About NYC, DC, and Maryland"

---

I spent the last few weeks building a market analysis pipeline for multifamily real estate — applying the kind of analytical workflows I've developed in a professional real estate environment, but fully open-sourced and reproducible. Here's what I built, what the data actually says, and why Maryland might be the most overlooked market in the Mid-Atlantic.

**[Live Dashboard →](https://your-app.streamlit.app)** | **[GitHub →](https://github.com/YOUR_USERNAME/real-estate-market-dashboard)**

---

### The Setup

Three markets. Six years of monthly rent data. One question: where would you put capital right now?

**Markets analyzed:** New York City · Washington DC · Maryland Suburbs (Rockville, Bethesda, Silver Spring)

**Data sources:** Zillow Research ZORI, HUD Fair Market Rents, US Census Bureau ACS

---

### The Pipeline

This wasn't just a dashboard — I built the full data engineering stack behind it:

1. **Ingestion** — Python scripts pulling public CSVs from Zillow Research
2. **Cleaning** — pandas transformations: wide-to-long melting, partial city name matching, MoM/YoY computation
3. **Storage** — SQLite database with window function queries (rolling averages, LAG/LEAD trends, ranked growth months)
4. **Forecasting** — Meta Prophet time series model with 80% uncertainty bands (R² > 0.993 across all three markets)
5. **Delivery** — Two outputs: an Excel dashboard (4 tabs, embedded charts, executive summary) and a live Streamlit web app with interactive filters

Full CI/CD via GitHub Actions: 21 unit tests run on every push, followed by the complete pipeline.

---

### What the Data Says

**New York City** — Highest rents ($3,683/mo), fastest absolute dollar growth. The COVID-19 correction was real: rents dropped roughly 10% from mid-2020 through early 2021. But the recovery was sharp. NYC is now up +5.9% YoY and showing the strongest post-pandemic momentum.

**Washington DC** — The most consistent performer. Minimal COVID volatility, steady +5.1% YoY growth. Government employment provides a floor that other markets don't have. If you want predictable, DC is it.

**Maryland Suburbs** — The most interesting story. Fastest YoY growth (+10.5%) and the *lowest* rent-to-income ratio at 29.7% — just below the 30% affordability threshold where economists start flagging cost burden. That combination (fast growth + accessible prices) is exactly what you look for in a near-term acquisition target.

All three markets have vacancy rates below 5% as of 2024 — a strong landlord-favorable signal across the board.

---

### The Forecast

Using Meta Prophet's trend + seasonality decomposition, all three markets are projected to see continued rent appreciation through 2025:

- **Maryland Suburbs:** $2,763 → ~$3,002/mo (+8.6%)
- **Washington DC:** $2,834 → continued steady growth
- **New York City:** $3,683 → projected to widen the lead

These are directional estimates with 80% confidence intervals — not guarantees. The model doesn't know about recessions, but it does capture the seasonal rhythm (summer peaks, winter softening) that's consistent across all three markets.

---

### Key Takeaway

Maryland Suburbs is the most compelling near-term play: fastest growth, most affordable relative to local incomes, and tight vacancy. DC is the low-risk, steady-return market. NYC rewards investors who can absorb the volatility and hold through cycles.

---

### Technical Notes (for the data folks)

- Forecast model: Meta Prophet with `changepoint_prior_scale=0.05` (conservative trend flexibility), yearly seasonality enabled, 80% credible intervals
- Affordability Index: (monthly rent × 12) ÷ median household income × 100
- Vacancy data from Census/CoStar annual estimates — not continuous series
- Full methodology in the README

---

*If you're working on real estate data, market analysis, or just want to see how the pipeline is built — the full code is on GitHub. Happy to connect.*

**#RealEstate #DataAnalysis #Python #DataEngineering #PropTech #Streamlit #MarketAnalysis**
