import time
import requests
from datetime import datetime, timezone

from models.price import CryptoPrice
from utils.db.index import SessionLocal
from utils.db.seed import seed

COIN_TICKERS = ["btc", "eth", "ada"]
COIN_IDS = ["bitcoin", "ethereum", "cardano"]


def fetch_and_save():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ",".join(COIN_IDS),
        "order": "market_cap_desc",
        "sparkline": "false",
    }
    try:
        response = requests.get(url, params=params).json()
        db = SessionLocal()

        print(f"[{datetime.now()}] Fetched data: {response}")

        for coin_data in response:

            new_entry = CryptoPrice(
                name=coin_data["id"],
                ticker=coin_data["symbol"].upper(),
                price_usd=round(float(coin_data["current_price"]), 2),
            )
            db.add(new_entry)

        db.commit()
        db.close()
    except Exception as e:
        print(f"Error while fetching data: {e}")


def backfill_coin_missing_data(coin_id, ticker):
    db = SessionLocal()
    last_entry = (
        db.query(CryptoPrice)
        .filter(CryptoPrice.ticker == coin_id)
        .order_by(CryptoPrice.timestamp.desc())
        .first()
    )

    if not last_entry:
        return

    start_ts = int(last_entry.timestamp.timestamp())
    end_ts = int(datetime.now(timezone.utc).timestamp())

    if end_ts - start_ts < 600:
        db.close()
        return

    print(f"Uzupełnianie brakujących danych dla {coin_id}...")

    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
    params = {"vs_currency": "usd", "from": start_ts, "to": end_ts}

    try:
        response = requests.get(url, params=params).json()
        for entry in response.get("prices", []):
            ts_ms, price = entry
            if ts_ms / 1000 > start_ts + 1:
                new_price = CryptoPrice(
                    name=coin_id,
                    ticker=ticker.upper(),
                    price_usd=round(float(price), 2),
                    timestamp=datetime.fromtimestamp(ts_ms / 1000),
                )
                db.add(new_price)
        db.commit()
    except Exception as e:
        print(f"Błąd backfill: {e}")
    finally:
        db.close()


def backfill_all():
    for coin_id, ticker in zip(COIN_IDS, COIN_TICKERS):
        backfill_coin_missing_data(coin_id, ticker)


if __name__ == "__main__":
    seed()
    backfill_all()
    print("Starting data collector...")
    while True:
        fetch_and_save()
        time.sleep(60)
