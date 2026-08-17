"""Download real historical market data from Yahoo Finance and format for QuantLab."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
import yfinance as yf


TICKERS = [
    ("AAPL", "Apple Inc.", "NASDAQ", False),
    ("MSFT", "Microsoft Corporation", "NASDAQ", False),
    ("GOOGL", "Alphabet Inc.", "NASDAQ", False),
    ("AMZN", "Amazon.com Inc.", "NASDAQ", False),
    ("META", "Meta Platforms Inc.", "NASDAQ", False),
    ("NVDA", "NVIDIA Corporation", "NASDAQ", False),
    ("TSLA", "Tesla Inc.", "NASDAQ", False),
    ("JPM", "JPMorgan Chase & Co.", "NYSE", False),
    ("V", "Visa Inc.", "NYSE", False),
    ("UNH", "UnitedHealth Group Inc.", "NYSE", False),
    ("PG", "Procter & Gamble Co.", "NYSE", False),
    ("XOM", "Exxon Mobil Corporation", "NYSE", False),
    ("JNJ", "Johnson & Johnson", "NYSE", False),
    ("HD", "The Home Depot Inc.", "NYSE", False),
    ("SPY", "SPDR S&P 500 ETF Trust", "NYSE", True),
    ("QQQ", "Invesco QQQ Trust", "NASDAQ", True),
]


def download_real_dataset() -> None:
    out_dir = Path("data/fixtures/us_megacap/source")
    out_dir.mkdir(parents=True, exist_ok=True)

    symbols = [t[0] for t in TICKERS]
    print(f"Downloading real historical price data for {len(symbols)} tickers: {symbols}...")

    # 1. Write listings.csv
    listings_path = out_dir / "listings.csv"
    with open(listings_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["symbol", "name", "exchange", "listed_date", "delisted_date", "is_etf"])
        for sym, name, exch, is_etf in TICKERS:
            writer.writerow([sym, name, exch, "1990-01-01", "", is_etf])

    # 2. Download and write prices.csv & actions.csv
    prices_path = out_dir / "prices.csv"
    actions_path = out_dir / "actions.csv"
    fund_path = out_dir / "fundamentals.csv"

    all_prices = []
    all_actions = []

    start_date = "2020-01-01"
    end_date = "2024-12-31"

    data = yf.download(symbols, start=start_date, end=end_date, group_by="ticker", auto_adjust=False)

    for sym, _, _, _ in TICKERS:
        try:
            df = data[sym] if len(symbols) > 1 else data
            df = df.dropna(how="all")
            for dt_idx, row in df.iterrows():
                dt_str = dt_idx.strftime("%Y-%m-%d")
                o = float(row["Open"])
                h = float(row["High"])
                l = float(row["Low"])
                c = float(row["Close"])
                v = int(row["Volume"]) if not row["Volume"] != row["Volume"] else 1000000

                if o > 0 and h > 0 and l > 0 and c > 0:
                    all_prices.append([dt_str, sym, f"{o:.2f}", f"{h:.2f}", f"{l:.2f}", f"{c:.2f}", str(v)])
        except Exception as e:
            print(f"Warning downloading {sym}: {e}")

    # Write prices.csv
    all_prices.sort(key=lambda x: (x[0], x[1]))
    with open(prices_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
        writer.writerows(all_prices)

    # Write synthetic corporate actions & fundamentals for these tickers
    with open(actions_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["effective_at", "available_at", "symbol", "action_type", "ratio", "cash_amount"])
        writer.writerow(["2020-08-31", "2020-08-30 20:00:00", "AAPL", "SPLIT", "4.0", ""])
        writer.writerow(["2022-08-25", "2022-08-24 20:00:00", "TSLA", "SPLIT", "3.0", ""])
        writer.writerow(["2024-06-10", "2024-06-09 20:00:00", "NVDA", "SPLIT", "10.0", ""])

    with open(fund_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["symbol", "as_reported_at", "effective_date", "metric_name", "metric_value"])
        for sym, _, _, is_etf in TICKERS:
            if not is_etf:
                writer.writerow([sym, "2020-02-15 16:00:00", "2019-12-31", "eps_diluted", "4.50"])
                writer.writerow([sym, "2020-02-15 16:00:00", "2019-12-31", "total_equity", "80000000000"])
                writer.writerow([sym, "2021-02-15 16:00:00", "2020-12-31", "eps_diluted", "5.20"])
                writer.writerow([sym, "2022-02-15 16:00:00", "2021-12-31", "eps_diluted", "6.10"])
                writer.writerow([sym, "2023-02-15 16:00:00", "2022-12-31", "eps_diluted", "7.00"])

    print(f"Downloaded {len(all_prices)} daily bars for {len(symbols)} tickers to {out_dir}")


if __name__ == "__main__":
    download_real_dataset()
