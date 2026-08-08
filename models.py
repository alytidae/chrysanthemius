import enum
import logging
import datetime
from peewee import *

logger = logging.getLogger(__name__)

db = SqliteDatabase('database.db')

class BaseModel(Model):
    class Meta:
        database = db

class Currency(BaseModel):
    code = CharField(unique=True, max_length=10)

class Category(BaseModel):
    name = CharField(unique=True)

class Message(BaseModel):
    role = CharField(
        max_length=9,
        constraints=[
            Check("role IN ('user', 'assistant')")
        ],
    )
    content = TextField()
    created_at = DateTimeField(default=datetime.datetime.now)

class Fact(BaseModel):
    content = TextField()
    created_at = DateTimeField(default=datetime.datetime.now)
 
class Account(BaseModel):
    name = CharField()
    description = TextField(null=True)

class PlannedPayment(BaseModel):
    description = TextField()
    amount = DecimalField(
        max_digits=36,
        decimal_places=18,
        auto_round=False,
    )
    currency = ForeignKeyField(Currency)
    due_at = DateTimeField(null=True)
    recurrence = CharField(null=True)
    is_active = BooleanField(default=True)

class TransactionType(enum.StrEnum):
    EXPENSE = "expense"
    INCOME = "income"
    TRANSFER = "transfer"
    REFUND = "refund"

class Transaction(BaseModel):
    account = ForeignKeyField(Account)
    amount = DecimalField(
        max_digits=36,
        decimal_places=18,
        auto_round=False,
    )
    currency = ForeignKeyField(Currency)
    transaction_type = CharField(
        max_length=16,
        constraints=[Check("transaction_type IN ('expense', 'income', 'transfer', 'refund')")],
    )
    category = ForeignKeyField(Category, null=True)
    description = TextField(null=True)
    occurred_at = DateTimeField()
    created_at = DateTimeField(default=datetime.datetime.now)

def init_db():
    db.connect()
    logger.info("Connected to db")
    db.create_tables([
        Currency, 
        Category, 
        Message, 
        Fact,
        Account,
        PlannedPayment,
        Transaction, 
    ])
    logger.info("Updated db tables")
