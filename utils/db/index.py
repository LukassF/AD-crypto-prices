from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

_engine = None

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# singleton pattern for database engine
def get_db():
    global _engine
    if not _engine:
        if not DATABASE_URL:
            raise ValueError("No DATABASE_URL in env!")
        _engine = create_engine(DATABASE_URL)
    return _engine
