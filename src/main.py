"""
Risk & Volatility Intelligence Apify Actor Entry Point.
Orchestrates multi-source historical price acquisition, quantitative risk metric computation,
and pushes structured institutional risk dossiers to the Apify Dataset.
"""

import sys
from datetime import datetime
import pytz
from apify import Actor

from .data_engine import fetch_historical_prices, clean_symbol
from .risk_calculator import compute_risk_analytics


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        symbols_input = actor_input.get("symbols", ["SPY", "QQQ", "AAPL", "NVDA"])
        years_back = int(actor_input.get("yearsBack", 5))
        start_date = actor_input.get("startDate")
        end_date = actor_input.get("endDate")
        risk_free_rate = float(actor_input.get("riskFreeRate", 4.0))
        rolling_window = int(actor_input.get("rollingWindow", 252))
        include_ts = actor_input.get("includeTimeSeries", True)
        include_dist = actor_input.get("includeReturnDistribution", True)

        if isinstance(symbols_input, str):
            symbols = [s.strip().upper() for s in symbols_input.replace(",", " ").split() if s.strip()]
        else:
            symbols = [str(s).strip().upper() for s in symbols_input if str(s).strip()]

        if not symbols:
            symbols = ["SPY", "QQQ", "AAPL", "NVDA"]

        utc_now = datetime.now(pytz.utc).isoformat()
        Actor.log.info("🛡️ Starting Risk & Volatility Intelligence Actor...")
        Actor.log.info(f"Target Assets: {symbols} | Years: {years_back} | RF Rate: {risk_free_rate}% | Rolling Window: {rolling_window}D")

        processed_count = 0
        summary_rankings = []

        for sym in symbols:
            clean_sym = clean_symbol(sym)
            Actor.log.info(f"Analyzing quantitative risk metrics for {clean_sym}...")

            prices, asset_name, provider = fetch_historical_prices(
                clean_sym,
                years_back=years_back,
                start_date=start_date,
                end_date=end_date
            )

            if prices is None or len(prices) < 10:
                Actor.log.warning(f"⚠️ Insufficient price data available for {clean_sym}. Skipping.")
                continue

            risk_data = compute_risk_analytics(
                prices,
                risk_free_rate_pct=risk_free_rate,
                rolling_window=rolling_window,
                include_timeseries=include_ts,
                include_distribution=include_dist
            )

            if not risk_data:
                continue

            # Build Dataset Record
            dataset_record = {
                "symbol": clean_sym,
                "name": asset_name,
                "dataProvider": provider,
                "timestamp": utc_now,
                "latestPrice": risk_data["latest_closing_price"],
                "currentSharpe": risk_data["current_sharpe_ratio"],
                "currentSortino": risk_data["current_sortino_ratio"],
                "calmarRatio": risk_data["calmar_ratio"],
                "maxDrawdownPct": risk_data["max_drawdown_pct"],
                "avgDrawdownRecoveryDays": risk_data["average_drawdown_recovery_business_days"],
                "longestDrawdownDays": risk_data["longest_drawdown_business_days"],
                "annualizedVolatilityPct": risk_data["annualized_volatility_pct"],
                "annualizedCagrPct": risk_data["annualized_cagr_pct"],
                "totalPeriodReturnPct": risk_data["total_period_return_pct"],
                "valueAtRisk95Pct": risk_data["value_at_risk"]["daily_var_95_pct"],
                "valueAtRisk99Pct": risk_data["value_at_risk"]["daily_var_99_pct"],
                "expectedShortfall95Pct": risk_data["value_at_risk"]["daily_expected_shortfall_cvar_95_pct"],
                "drawdownEvents": risk_data["drawdown_events_ledger"],
                "riskAssessment": risk_data["risk_assessment"],
                "analyticsHorizon": {
                    "startDate": risk_data["start_date"],
                    "endDate": risk_data["end_date"],
                    "tradingDays": risk_data["trading_days_analyzed"]
                }
            }

            if include_ts:
                dataset_record["drawdownSeries"] = risk_data.get("drawdown_series")
                dataset_record["rollingSharpeSeries"] = risk_data.get("rolling_sharpe_1y_series")

            if include_dist:
                dataset_record["returnDistribution"] = risk_data.get("return_distribution")

            await Actor.push_data(dataset_record)
            processed_count += 1

            summary_rankings.append({
                "symbol": clean_sym,
                "name": asset_name,
                "currentSharpe": risk_data["current_sharpe_ratio"],
                "currentSortino": risk_data["current_sortino_ratio"],
                "maxDrawdownPct": risk_data["max_drawdown_pct"],
                "annualizedVolatilityPct": risk_data["annualized_volatility_pct"],
                "annualizedCagrPct": risk_data["annualized_cagr_pct"],
                "riskGrade": risk_data["risk_assessment"]["grade"]
            })

        # Sort summary rankings by Sharpe ratio descending
        summary_rankings.sort(key=lambda x: x["currentSharpe"], reverse=True)

        # Store Executive Summary in Key-Value Store
        exec_summary = {
            "actor_run_timestamp": utc_now,
            "assets_analyzed_count": processed_count,
            "assumed_risk_free_rate_pct": risk_free_rate,
            "top_risk_adjusted_performer": summary_rankings[0]["symbol"] if summary_rankings else None,
            "cross_asset_rankings": summary_rankings,
            "status": "SUCCESS"
        }
        await Actor.set_value("OUTPUT_RISK_SUMMARY", exec_summary)

        Actor.log.info(f"✅ Risk & Volatility Intelligence Actor completed! {processed_count} asset dossiers pushed to Apify Dataset.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
