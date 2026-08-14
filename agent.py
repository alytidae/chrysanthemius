import datetime

from pydantic_ai import Agent, DeferredToolRequests
from peewee import IntegrityError
from peewee import fn

from models import Transaction, Account, Currency, Category, Fact, PlannedPayment, TransactionType
from playhouse.shortcuts import model_to_dict

FINANCE_INSTRUCTIONS = """
You are a personal finance assistant.
Determine whether the user wants to record a transaction or receive financial information and advice.
When the user reports an expense, income, transfer, or refund, extract the transaction type, amount, description, and date. If important information is missing, ask one concise clarifying question. Otherwise, use the appropriate tool and confirm the transaction only after it has been saved successfully.
When the user asks about their finances, retrieve the relevant data using the available tools. Never invent transactions, amounts, balances, or statistics. Explain the results clearly and provide concise, practical recommendations.
Respond in the user's language. Be calm, supportive, and professional.
"""

agent = Agent(
    "deepseek:deepseek-chat",
    instructions=FINANCE_INSTRUCTIONS,
    output_type=[str, DeferredToolRequests],
)

@agent.tool_plain()
def get_accounts() -> list[dict]:
    """
    List all accounts.
    """
    return list(Account.select().dicts())

@agent.tool_plain(requires_approval=True)
def create_account(name, description) -> dict:
    """
    Create a new account.
    Args:
        name: account name
        description: account description
    """
    return model_to_dict(
        Account.create(name=name, description=description)
    )

@agent.tool_plain(requires_approval=True)
def update_account(account_id: int, name: str = None, description: str = None) -> dict:
    """
    Update an existing account.
    Args:
        account_id: account id
        name: new account name
        description: new account description
    """
    account = Account.get_or_none(Account.id == account_id)
    if not account:
        return {"error": "Account not found"}
    if name is not None:
        account.name = name
    if description is not None:
        account.description = description
    account.save()
    return model_to_dict(account)

@agent.tool_plain(requires_approval=True)
def delete_account(account_id: int) -> dict:
    """
    Delete an account by id.
    Args:
        account_id: account id
    """
    account = Account.get_or_none(Account.id == account_id)
    if not account:
        return {"error": "Account not found"}
    count = Transaction.select().where(Transaction.account == account).count()
    if count:
        return {"error": f"This account is still in use: {count} transactions reference it"}
    account.delete_instance()
    return {"ok": True, "message": f"Account {account.name!r} deleted"}

@agent.tool_plain()
def get_currencies() -> list[dict]:
    """
    List all currencies.
    """
    return list(Currency.select().dicts())

@agent.tool_plain(requires_approval=True)
def create_currency(code: str) -> dict:
    """
    Create a new currency.
    Args:
        code: currency code, e.g. USD, EUR
    """
    try:
        currency = Currency.create(code=code)
    except IntegrityError:
        return {"error": f"Currency {code!r} already exists"}
    return model_to_dict(currency)

@agent.tool_plain(requires_approval=True)
def update_currency(currency_id: int, code: str = None) -> dict:
    """
    Update an existing currency.
    Args:
        currency_id: currency id
        code: new currency code
    """
    currency = Currency.get_or_none(Currency.id == currency_id)
    if not currency:
        return {"error": "Currency not found"}
    if code is not None:
        currency.code = code
        try:
            currency.save()
        except IntegrityError:
            return {"error": f"Currency {code!r} already exists"}
    return model_to_dict(currency)

@agent.tool_plain(requires_approval=True)
def delete_currency(currency_id: int) -> dict:
    """
    Delete a currency by id.
    Args:
        currency_id: currency id
    """
    currency = Currency.get_or_none(Currency.id == currency_id)
    if not currency:
        return {"error": "Currency not found"}
    usage = (
        Transaction.select().where(Transaction.currency == currency).count()
        + PlannedPayment.select().where(PlannedPayment.currency == currency).count()
    )
    if usage:
        return {"error": f"This currency is still in use: {usage} transactions/planned payments reference it"}
    currency.delete_instance()
    return {"ok": True, "message": f"Currency {currency.code!r} deleted"}

@agent.tool_plain()
def get_categories() -> list[dict]:
    """
    List all categories.
    """
    return list(Category.select().dicts())

@agent.tool_plain(requires_approval=True)
def create_category(name: str) -> dict:
    """
    Create a new category.
    Args:
        name: category name
    """
    try:
        category = Category.create(name=name)
    except IntegrityError:
        return {"error": f"Category {name!r} already exists"}
    return model_to_dict(category)

@agent.tool_plain(requires_approval=True)
def update_category(category_id: int, name: str = None) -> dict:
    """
    Update an existing category.
    Args:
        category_id: category id
        name: new category name
    """
    category = Category.get_or_none(Category.id == category_id)
    if not category:
        return {"error": "Category not found"}
    if name is not None:
        category.name = name
        try:
            category.save()
        except IntegrityError:
            return {"error": f"Category {name!r} already exists"}
    return model_to_dict(category)

@agent.tool_plain(requires_approval=True)
def delete_category(category_id: int) -> dict:
    """
    Delete a category by id.
    Args:
        category_id: category id
    """
    category = Category.get_or_none(Category.id == category_id)
    if not category:
        return {"error": "Category not found"}
    count = Transaction.select().where(Transaction.category == category).count()
    if count:
        return {"error": f"This category is still in use: {count} transactions reference it"}
    category.delete_instance()
    return {"ok": True, "message": f"Category {category.name!r} deleted"}

@agent.tool_plain()
def get_facts() -> list[dict]:
    """
    List all facts.
    """
    return list(Fact.select().dicts())

@agent.tool_plain(requires_approval=True)
def create_fact(content: str) -> dict:
    """
    Create a new fact.
    Args:
        content: fact text
    """
    return model_to_dict(Fact.create(content=content))

@agent.tool_plain(requires_approval=True)
def update_fact(fact_id: int, content: str) -> dict:
    """
    Update an existing fact.
    Args:
        fact_id: fact id
        content: new fact text
    """
    fact = Fact.get_or_none(Fact.id == fact_id)
    if not fact:
        return {"error": "Fact not found"}
    fact.content = content
    fact.save()
    return model_to_dict(fact)

@agent.tool_plain(requires_approval=True)
def delete_fact(fact_id: int) -> dict:
    """
    Delete a fact by id.
    Args:
        fact_id: fact id
    """
    fact = Fact.get_or_none(Fact.id == fact_id)
    if not fact:
        return {"error": "Fact not found"}
    fact.delete_instance()
    return {"ok": True, "message": "Fact deleted"}

@agent.tool_plain()
def get_planned_payments() -> list[dict]:
    """
    List all planned payments.
    """
    return list(PlannedPayment.select().dicts())

@agent.tool_plain(requires_approval=True)
def create_planned_payment(
        description: str,
        amount: float,
        currency_id: int,
        due_at: str = None,
        recurrence: str = None) -> dict:
    """
    Create a new planned payment.
    Args:
        description: payment description
        amount: payment amount
        currency_id: currency id
        due_at: due date in ISO format (optional)
        recurrence: recurrence rule, e.g. monthly (optional)
    """
    currency = Currency.get_or_none(Currency.id == currency_id)
    if not currency:
        return {"error": "Currency not found"}
    if due_at is not None:
        try:
            due_at = datetime.fromisoformat(due_at)
        except ValueError:
            return {"error": f"Invalid date: {due_at!r}"}
    return model_to_dict(
        PlannedPayment.create(
            description=description,
            amount=amount,
            currency=currency,
            due_at=due_at,
            recurrence=recurrence,
        )
    )

@agent.tool_plain(requires_approval=True)
def update_planned_payment(
        payment_id: int,
        description: str = None,
        amount: float = None,
        currency_id: int = None,
        due_at: str = None,
        recurrence: str = None) -> dict:
    """
    Update an existing planned payment.
    Args:
        payment_id: planned payment id
        description: new payment description
        amount: new payment amount
        currency_id: new currency id
        due_at: new due date (ISO format)
        recurrence: new recurrence rule
    """
    payment = PlannedPayment.get_or_none(PlannedPayment.id == payment_id)
    if not payment:
        return {"error": "Planned payment not found"}
    if description is not None:
        payment.description = description
    if amount is not None:
        payment.amount = amount
    if currency_id is not None:
        currency = Currency.get_or_none(Currency.id == currency_id)
        if not currency:
            return {"error": "Currency not found"}
        payment.currency = currency
    if due_at is not None:
        try:
            payment.due_at = datetime.fromisoformat(due_at)
        except ValueError:
            return {"error": f"Invalid date: {due_at!r}"}
    if recurrence is not None:
        payment.recurrence = recurrence
    payment.save()
    return model_to_dict(payment)

@agent.tool_plain(requires_approval=True)
def delete_planned_payment(payment_id: int) -> dict:
    """
    Delete a planned payment by id.
    Args:
        payment_id: planned payment id
    """
    payment = PlannedPayment.get_or_none(PlannedPayment.id == payment_id)
    if not payment:
        return {"error": "Planned payment not found"}
    payment.delete_instance()
    return {"ok": True, "message": "Planned payment deleted"}

@agent.tool_plain(requires_approval=True)
def create_transaction(
        account_id: int,
        amount: float,
        currency_id: int,
        transaction_type: TransactionType,
        description: str,
        occurred_at_str: str,
        category_id: int = None,
    ) -> dict:
    """
    Create a new transaction.
    Args:
        account_id: account id
        amount: transaction amount
        currency_id: currency id
        transaction_type: transaction type (expense, income, transfer, refund)
        description: transaction description
        occurred_at_str: date in ISO format
        category_id: category id (optional)
    """
    account = Account.get_or_none(Account.id == account_id)
    if account is None:
        return {"error": "Account not found"}

    currency = Currency.get_or_none(Currency.id == currency_id)
    if currency is None:
        return {"error": "Currency not found"}

    category = None
    if category_id is not None:
        category = Category.get_or_none(Category.id == category_id)
        if category is None:
            return {"error": "Category not found"}

    try:
        occurred_at = datetime.fromisoformat(occurred_at_str)
    except ValueError:
        return {"error": f"Invalid date: {occurred_at_str!r}"}

    return model_to_dict(
        Transaction.create(
            account=account,
           amount=amount,
           currency=currency,
           transaction_type=transaction_type,
           category=category,
           description=description,
           occurred_at=occurred_at)
        )

@agent.tool_plain(requires_approval=True)
def update_transaction(
        transaction_id: int,
        account_id: int = None,
        amount: float = None,
        currency_id: int = None,
        transaction_type: TransactionType = None,
        category_id: int = None,
        description: str = None,
        occurred_at_str: str = None) -> dict:
    """
    Update an existing transaction.
    Args:
        transaction_id: transaction id
        account_id: new account id
        amount: new amount
        currency_id: new currency id
        transaction_type: new transaction type
        category_id: new category id
        description: new description
        occurred_at_str: new date in ISO format
    """
    transaction = Transaction.get_or_none(Transaction.id == transaction_id)
    if not transaction:
        return {"error": "Transaction not found"}

    if account_id is not None:
        account = Account.get_or_none(Account.id == account_id)
        if not account:
            return {"error": "Account not found"}
        transaction.account = account

    if amount is not None:
        transaction.amount = amount

    if currency_id is not None:
        currency = Currency.get_or_none(Currency.id == currency_id)
        if not currency:
            return {"error": "Currency not found"}
        transaction.currency = currency

    if transaction_type is not None:
        transaction.transaction_type = transaction_type

    if category_id is not None:
        category = Category.get_or_none(Category.id == category_id)
        if not category:
            return {"error": "Category not found"}
        transaction.category = category

    if description is not None:
        transaction.description = description

    if occurred_at_str is not None:
        try:
            transaction.occurred_at = datetime.fromisoformat(occurred_at_str)
        except ValueError:
            return {"error": f"Invalid date: {occurred_at_str!r}"}

    transaction.save()
    return model_to_dict(transaction)

@agent.tool_plain(requires_approval=True)
def delete_transaction(transaction_id: int) -> dict:
    """
    Delete a transaction by id.
    Args:
        transaction_id: transaction id
    """
    transaction = Transaction.get_or_none(Transaction.id == transaction_id)
    if not transaction:
        return {"error": "Transaction not found"}
    transaction.delete_instance()
    return {"ok": True, "message": "Transaction deleted"}

def get_current_month_transactions() -> dict:
    month_start = datetime.today().replace(day=1)
    return list(Transaction.select(Transaction.occured_at >= month_start).dicts())

def get_current_month_spendings_by_category() -> dict:
    month_start = datetime.today().replace(day=1)

    query = (
        Transaction
        .select(
            Category.name,
            fn.SUM(Transaction.amount).alias("total"),
        )
        .join(Category)
        .where(
            Transaction.occured_at >= month_start
        )
        .group_by(Category.id, Category.name)
    )

    rows = query.dicts()

    result = {
        row["name"]: row["total"]
        for row in rows
    }
