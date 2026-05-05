import time
import requests
import os
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from sqlalchemy.sql import func

from models.price import CryptoPrice
from utils.db.index import SessionLocal
from utils.db.seed import seed


def fetch_and_save():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": "bitcoin,ethereum,cardano",
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
                price_usd=coin_data["current_price"],
            )
            db.add(new_entry)

        db.commit()
        db.close()
    except Exception as e:
        print(f"Error while fetching data: {e}")


if __name__ == "__main__":
    seed()
    print("Starting data collector...")
    while True:
        fetch_and_save()
        time.sleep(60)
