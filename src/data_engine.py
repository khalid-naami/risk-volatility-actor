"""
Multi-source Financial Data Fetcher (Yahoo Finance + Stooq Fallback).
"""

from datetime import datetime, timedelta
import io
import requests
import pandas as pd
import yfinance as yf


def clean_symbol(sym: str) -> str:
    """Normalize symbol string."""
    s = sym.strip().upper()
    if s == "SPX":
        return "^SPX"
    elif s == "NDX":
        return "^NDX"
    elif s == "VIX":
        return "^VIX"
    elif s == "RUT":
        return "^RUT"
    elif s == "DJI":
        return "^DJI"
    return s


def fetch_historical_prices(symbol: str, years_back: int = 5, start_date: str = None, end_date: str = None):
    """Fetch daily adjusted close price series for any symbol."""
    norm_sym = clean_symbol(symbol)
    asset_name = norm_sym

    # Calculate date boundary
    if not end_date:
        end_dt = datetime.now()
    else:
        end_dt = pd.to_datetime(end_date)

    if not start_date:
        start_dt = end_dt - timedelta(days=int(years_back * 365.25))
    else:
        start_dt = pd.to_datetime(start_date)

    # 1. Primary Source: Yahoo Finance
    try:
        ticker_obj = yf.Ticker(norm_sym)
        df_yf = ticker_obj.history(start=start_dt.strftime("%Y-%m-%d"), end=end_dt.strftime("%Y-%m-%d"), auto_adjust=True)
        if df_yf is not None and not df_yf.empty and len(df_yf) >= 10:
            info = ticker_obj.info or {}
            asset_name = info.get("shortName") or info.get("longName") or norm_sym
            close_series = df_yf['Close'].ffill().dropna()
            close_series.index = pd.to_datetime(close_series.index).tz_localize(None)
            return close_series, asset_name, "Yahoo Finance"
    except Exception:
        pass

    # 2. Secondary Fallback: Stooq Direct CSV
    try:
        stooq_sym = norm_sym.lower().replace("^", "")
        if not stooq_sym.endswith(".us") and not "." in stooq_sym:
            stooq_sym = f"{stooq_sym}.us"
        stooq_url = f"https://stooq.com/q/d/l/?s={stooq_sym}&i=d"
        resp = requests.get(stooq_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if resp.status_code == 200 and "Date" in resp.text:
            df_stooq = pd.read_csv(io.StringIO(resp.text))
            if not df_stooq.empty and "Close" in df_stooq.columns:
                df_stooq['Date'] = pd.to_datetime(df_stooq['Date'])
                df_stooq.sort_values('Date', inplace=True)
                df_stooq.set_index('Date', inplace=True)
                df_filtered = df_stooq[(df_stooq.index >= start_dt) & (df_stooq.index <= end_dt)]
                if not df_filtered.empty and len(df_filtered) >= 10:
                    close_series = df_filtered['Close'].ffill().dropna()
                    return close_series, norm_sym, "Stooq"
    except Exception:
        pass

    return None, norm_sym, None
