# 🛡️ Risk & Volatility Intelligence Actor

**Quantitative risk profiling, peak drawdown analysis, recovery timelines, rolling Sharpe ratios, and Value at Risk (VaR / CVaR) across global Stocks, ETFs, Crypto, Forex, Indices, and Commodities.**

---

## 🌟 Overview

The **Risk & Volatility Intelligence Actor** calculates quantitative risk and portfolio protection metrics used by hedge funds and institutional risk managers:

1. **Risk-Adjusted Performance Ratios:**
   - **Annualized Sharpe Ratio:** Measures excess return per unit of total risk against a configurable risk-free rate.
   - **Annualized Sortino Ratio:** Measures excess return against downside volatility only (ignores upside volatility).
   - **Calmar Ratio:** Compound annual return (CAGR) relative to the maximum peak drawdown.
2. **Drawdown Profile & Peak-to-Trough Recovery Timelines:**
   - Maximum historical drawdown percentage and day-by-day drawdown curve.
   - Granular **Drawdown Events Ledger** tracking every drawdown period: Start date, Trough date, Recovery date, duration in business days, and Ongoing status.
   - Average and longest recovery duration in trading days.
3. **1-Year (252-Day) Rolling Sharpe Ratio:**
   - Moving 1-year window Sharpe ratio time-series to track regime shifts in risk-adjusted performance.
4. **Return Distribution & Gaussian Fit (Bell Curve):**
   - 50-bin return frequency histogram, parametric Gaussian probability density function (PDF), Skewness, Kurtosis, and standard deviation bounds ($\mu \pm 1\sigma, \pm 2\sigma$).
5. **Value at Risk (VaR) & Expected Shortfall (CVaR):**
   - 95% and 99% daily Value at Risk and 95% Conditional Value at Risk (Expected Shortfall).

---

## 📥 Input Parameters

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `symbols` | Array / String | `["SPY", "QQQ", "AAPL", "NVDA"]` | Tickers or symbols to analyze. Supports Stocks, ETFs, Crypto (`BTC-USD`), Forex (`EURUSD=X`), Futures/Commodities (`GC=F`), and Indices (`^SPX`, `^NDX`, `^VIX`). |
| `yearsBack` | Integer | `5` | Historical lookback horizon in years (1 to 50). |
| `startDate` | String | `null` | Optional explicit start date (`YYYY-MM-DD`). |
| `endDate` | String | `null` | Optional explicit end date (`YYYY-MM-DD`). |
| `riskFreeRate` | Number | `4.0` | Annual risk-free rate percentage for Sharpe/Sortino ratios (e.g. `4.0` for 4%). |
| `rollingWindow` | Integer | `252` | Window size for rolling Sharpe calculations (default 252 trading days). |
| `includeTimeSeries` | Boolean | `true` | Include day-by-day drawdown series and rolling Sharpe curves in output. |
| `includeReturnDistribution` | Boolean | `true` | Include 50-bin histogram and Gaussian PDF curve. |

---

## 📤 Output Dataset Format

Each asset record in the dataset provides complete quantitative risk analytics:

```json
{
  "symbol": "SPY",
  "name": "SPDR S&P 500 ETF Trust",
  "dataProvider": "Yahoo Finance",
  "latestPrice": 570.25,
  "currentSharpe": 1.12,
  "currentSortino": 1.65,
  "calmarRatio": 0.58,
  "maxDrawdownPct": -25.49,
  "avgDrawdownRecoveryDays": 24.6,
  "longestDrawdownDays": 182,
  "annualizedVolatilityPct": 16.85,
  "annualizedCagrPct": 14.78,
  "totalPeriodReturnPct": 98.42,
  "valueAtRisk95Pct": -1.54,
  "valueAtRisk99Pct": -2.68,
  "expectedShortfall95Pct": -2.25,
  "drawdownEvents": [
    {
      "year": 2022,
      "duration_business_days": 182,
      "drawdown_start_date": "2022-01-04",
      "drawdown_trough_date": "2022-10-12",
      "recovery_end_date": "2023-12-14",
      "trough_drawdown_pct": -25.49,
      "is_ongoing": false
    }
  ],
  "riskAssessment": {
    "grade": "EXCELLENT RISK-ADJUSTED (TIER 1)",
    "color_tag": "EMERALD",
    "assumed_risk_free_rate_pct": 4.0
  }
}
```

---

## 💻 Python Client Usage

```python
from apify_client import ApifyClient

client = ApifyClient("<YOUR_APIFY_API_TOKEN>")

run = client.actor("your-username/risk-volatility-actor").call(run_input={
    "symbols": ["SPY", "QQQ", "BTC-USD", "NVDA", "AAPL"],
    "yearsBack": 5,
    "riskFreeRate": 4.0,
    "includeTimeSeries": True,
    "includeReturnDistribution": True
})

for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    print(f"Asset: {item['symbol']} | Sharpe: {item['currentSharpe']} | Max DD: {item['maxDrawdownPct']}%")
```
