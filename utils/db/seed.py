from utils.db.index import Base, engine

import models.price


def seed():
    Base.metadata.create_all(bind=engine)
