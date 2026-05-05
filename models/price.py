from sqlalchemy import Column, DateTime, Float, String
from utils.db.index import Base
from sqlalchemy.sql import func
import uuid


class CryptoPrice(Base):
    __tablename__ = "prices"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    ticker = Column(String)
    name = Column(String)
    price_usd = Column(Float)
    timestamp = Column(DateTime, default=func.now())
