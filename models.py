import logging
import datetime
from peewee import *

logger = logging.getLogger(__name__)

db = SqliteDatabase('database.db')

class BaseModel(Model):
    class Meta:
        database = db

class Transaction(BaseModel):
    amount = DecimalField()
    description = TextField()
    timestamp = DateTimeField(default=datetime.datetime.now)

    @classmethod
    def get_all_transaction_sum(cls):
        return cls.select(fn.SUM(cls.amount)).scalar()



def init_db():
    db.connect()
    logger.info("Connected to db")
    db.create_tables([Transaction])
    logger.info("Updated db tables")


