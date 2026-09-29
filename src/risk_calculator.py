"""
Institutional Quantitative Risk & Volatility Calculation Engine.
Calculates Sharpe, Sortino, Calmar, Peak Drawdown Series, Recovery Duration Timelines,
Rolling Sharpe Series, 50-bin Return Distributions, Gaussian PDF Fits, and VaR / CVaR.
"""

from datetime import datetime
import numpy as np
import pandas as pd
from scipy import stats


def compute_risk_analytics(
    prices: pd.Series,
    risk_free_rate_pct: float = 4.0,
    rolling_window: int = 252,
    include_timeseries: bool = True,
    include_distribution: bool = True
) -> dict:
    """Compute complete quantitative risk and volatility analytics for a price series."""
    if prices is None or len(prices) < 10:
        return None

    dates = prices.index
    n_days = len(prices)
    first_price = float(prices.iloc[0])
    last_price = float(prices.iloc[-1])
    total_return_pct = ((last_price - first_price) / first_price) * 100.0

    # Compound Annual Growth Rate (CAGR)
    years_elapsed = max(0.1, (dates[-1] - dates[0]).days / 365.25)
    cagr_pct = (((last_price / first_price) ** (1.0 / years_elapsed)) - 1.0) * 100.0 if first_price > 0 else 0.0

    # Daily Returns
    daily_returns = prices.pct_change().dropna()
    mean_daily_ret = float(daily_returns.mean())
    std_daily_ret = float(daily_returns.std())
    annualized_volatility_pct = std_daily_ret * np.sqrt(252) * 100.0

    # Risk-free rate daily conversion
    rf_daily = (risk_free_rate_pct / 100.0) / 252.0

    # ── 1. SHARPE & SORTINO RATIOS ───────────────────────────────────────────
    if std_daily_ret > 0:
        current_sharpe = float((mean_daily_ret - rf_daily) / std_daily_ret * np.sqrt(252))
    else:
        current_sharpe = 0.0

    # Sortino: Downside deviation below 0 (or Rf)
    downside_returns = daily_returns[daily_returns < rf_daily]
    if len(downside_returns) > 0 and downside_returns.std() > 0:
        downside_std = float(downside_returns.std())
        current_sortino = float((mean_daily_ret - rf_daily) / downside_std * np.sqrt(252))
    else:
        current_sortino = current_sharpe

    # ── 2. PEAK DRAWDOWN PROFILE & RECOVERY TIMELINES ─────────────────────────
    rolling_peak = prices.cummax()
    drawdown_series = (prices - rolling_peak) / rolling_peak * 100.0
    max_dd_pct = float(drawdown_series.min())

    # Historical Drawdown Events Scanner
    in_drawdown = False
    start_dt = None
    trough_val = 0.0
    trough_dt = None
    durations = []

    for i in range(len(drawdown_series)):
        val = float(drawdown_series.iloc[i])
        dt = dates[i]

        if val < -0.01:
            if not in_drawdown:
                in_drawdown = True
                start_dt = dt
                trough_val = val
                trough_dt = dt
            else:
                if val < trough_val:
                    trough_val = val
                    trough_dt = dt
        else:
            if in_drawdown:
                try:
                    bus_days = int(np.busday_count(start_dt.date(), dt.date()))
                except Exception:
                    bus_days = (dt - start_dt).days
                bus_days = max(1, bus_days)

                durations.append({
                    "year": int(dt.year),
                    "duration_business_days": bus_days,
                    "drawdown_start_date": start_dt.strftime("%Y-%m-%d"),
                    "drawdown_trough_date": trough_dt.strftime("%Y-%m-%d"),
                    "recovery_end_date": dt.strftime("%Y-%m-%d"),
                    "trough_drawdown_pct": round(trough_val, 2),
                    "is_ongoing": False
                })
                in_drawdown = False

    if in_drawdown:
        end_dt = dates[-1]
        try:
            bus_days = int(np.busday_count(start_dt.date(), end_dt.date()))
        except Exception:
            bus_days = (end_dt - start_dt).days
        bus_days = max(1, bus_days)

        durations.append({
            "year": int(end_dt.year),
            "duration_business_days": bus_days,
            "drawdown_start_date": start_dt.strftime("%Y-%m-%d"),
            "drawdown_trough_date": trough_dt.strftime("%Y-%m-%d"),
            "recovery_end_date": end_dt.strftime("%Y-%m-%d"),
            "trough_drawdown_pct": round(trough_val, 2),
            "is_ongoing": True
        })

    avg_recovery_days = float(np.mean([d["duration_business_days"] for d in durations])) if durations else 0.0
    longest_drawdown_days = int(np.max([d["duration_business_days"] for d in durations])) if durations else 0

    # Calmar Ratio
    calmar_ratio = float(cagr_pct / abs(max_dd_pct)) if abs(max_dd_pct) > 0 else 0.0

    # ── 3. ROLLING SHARPE RATIO (1-YEAR / 252-DAY) ───────────────────────────
    rolling_w = min(rolling_window, len(daily_returns))
    roll_mean = daily_returns.rolling(window=rolling_w).mean()
    roll_std = daily_returns.rolling(window=rolling_w).std()
    rolling_sharpe = ((roll_mean - rf_daily) / roll_std * np.sqrt(252)).dropna()

    # ── 4. VALUE AT RISK (VaR) & CONDITIONAL VaR (CVaR / EXPECTED SHORTFALL) ─
    ret_pct = daily_returns * 100.0
    var_95_historical = float(np.percentile(ret_pct, 5))
    var_99_historical = float(np.percentile(ret_pct, 1))
    cvar_95 = float(ret_pct[ret_pct <= var_95_historical].mean()) if len(ret_pct[ret_pct <= var_95_historical]) > 0 else var_95_historical

    # ── 5. RETURN DISTRIBUTION & GAUSSIAN BELL CURVE FIT ─────────────────────
    dist_payload = {}
    if include_distribution and len(daily_returns) > 0:
        n_bins = 50
        r_min = float(ret_pct.min())
        r_max = float(ret_pct.max())
        bin_width = (r_max - r_min) / n_bins if r_max > r_min else 0.1

        counts, bin_edges = np.histogram(ret_pct, bins=n_bins)
        bin_centers = [(bin_edges[i] + bin_edges[i+1]) / 2.0 for i in range(n_bins)]
        densities = [float(c / (len(ret_pct) * bin_width)) for c in counts]

        mu = float(mean_daily_ret * 100.0)
        sigma = float(std_daily_ret * 100.0)

        gaussian_pdf = []
        for x in bin_centers:
            if sigma > 0:
                exponent = -((x - mu) ** 2) / (2 * (sigma ** 2))
                pdf_val = (1.0 / (sigma * np.sqrt(2 * np.pi))) * np.exp(exponent)
            else:
                pdf_val = 0.0
            gaussian_pdf.append(round(float(pdf_val), 4))

        dist_payload = {
            "mean_daily_return_pct": round(mu, 4),
            "std_daily_return_pct": round(sigma, 4),
            "skewness": round(float(stats.skew(daily_returns)), 3),
            "kurtosis": round(float(stats.kurtosis(daily_returns)), 3),
            "sigma_levels": {
                "minus_2_sigma": round(mu - 2 * sigma, 2),
                "minus_1_sigma": round(mu - sigma, 2),
                "mean": round(mu, 2),
                "plus_1_sigma": round(mu + sigma, 2),
                "plus_2_sigma": round(mu + 2 * sigma, 2)
            },
            "binned_histogram": [
                {"bin_center_pct": round(float(bc), 3), "density": round(float(den), 4), "gaussian_fit": g_pdf}
                for bc, den, g_pdf in zip(bin_centers, densities, gaussian_pdf)
            ]
        }

    # ── 6. QUALITATIVE AI RISK PROFILE RATING ─────────────────────────────────
    if current_sharpe >= 1.5 and abs(max_dd_pct) <= 15:
        risk_grade = "EXCELLENT RISK-ADJUSTED (TIER 1)"
        risk_color = "EMERALD"
    elif current_sharpe >= 0.8 and abs(max_dd_pct) <= 25:
        risk_grade = "BALANCED / MODERATE RISK"
        risk_color = "BLUE"
    elif current_sharpe >= 0.3 and abs(max_dd_pct) <= 40:
        risk_grade = "ELEVATED DRAWDOWN RISK"
        risk_color = "YELLOW"
    else:
        risk_grade = "HIGH VOLATILITY / SPECULATIVE"
        risk_color = "RED"

    # Assemble complete payload
    result = {
        "start_date": dates[0].strftime("%Y-%m-%d"),
        "end_date": dates[-1].strftime("%Y-%m-%d"),
        "trading_days_analyzed": n_days,
        "latest_closing_price": round(last_price, 2),
        "total_period_return_pct": round(total_return_pct, 2),
        "annualized_cagr_pct": round(cagr_pct, 2),
        "annualized_volatility_pct": round(annualized_volatility_pct, 2),
        "current_sharpe_ratio": round(current_sharpe, 2),
        "current_sortino_ratio": round(current_sortino, 2),
        "calmar_ratio": round(calmar_ratio, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "average_drawdown_recovery_business_days": round(avg_recovery_days, 1),
        "longest_drawdown_business_days": longest_drawdown_days,
        "total_drawdown_events_logged": len(durations),
        "value_at_risk": {
            "daily_var_95_pct": round(var_95_historical, 2),
            "daily_var_99_pct": round(var_99_historical, 2),
            "daily_expected_shortfall_cvar_95_pct": round(cvar_95, 2)
        },
        "risk_assessment": {
            "grade": risk_grade,
            "color_tag": risk_color,
            "assumed_risk_free_rate_pct": risk_free_rate_pct
        },
        "drawdown_events_ledger": durations
    }

    if include_timeseries:
        result["drawdown_series"] = {
            "dates": [d.strftime("%Y-%m-%d") for d in drawdown_series.index],
            "values": [round(float(v), 2) for v in drawdown_series.values]
        }
        result["rolling_sharpe_1y_series"] = {
            "dates": [d.strftime("%Y-%m-%d") for d in rolling_sharpe.index],
            "values": [round(float(v), 3) for v in rolling_sharpe.values]
        }

    if include_distribution:
        result["return_distribution"] = dist_payload

    return result
