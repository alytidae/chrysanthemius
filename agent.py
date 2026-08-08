import datetime

from pydantic_ai import Agent, DeferredToolRequests
from peewee import IntegrityError

from models import Transaction, Account, Currency, Category, Fact, PlannedPayment
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
    return list(Account.select().dicts())

@agent.tool_plain(requires_approval=True)
def create_account(name, description) -> dict:
    return model_to_dict(
        Account.create(name=name, description=description)
    )

@agent.tool_plain(requires_approval=True)
def update_account(account_id: int, name: str = None, description: str = None) -> dict:
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
    return list(Currency.select().dicts())

@agent.tool_plain(requires_approval=True)
def create_currency(code: str) -> dict:
    try:
        currency = Currency.create(code=code)
    except IntegrityError:
        return {"error": f"Currency {code!r} already exists"}
    return model_to_dict(currency)

@agent.tool_plain(requires_approval=True)
def update_currency(currency_id: int, code: str = None) -> dict:
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
    return list(Category.select().dicts())

@agent.tool_plain(requires_approval=True)
def create_category(name: str) -> dict:
    try:
        category = Category.create(name=name)
    except IntegrityError:
        return {"error": f"Category {name!r} already exists"}
    return model_to_dict(category)

@agent.tool_plain(requires_approval=True)
def update_category(category_id: int, name: str = None) -> dict:
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
    return list(Fact.select().dicts())

@agent.tool_plain(requires_approval=True)
def create_fact(content: str) -> dict:
    return model_to_dict(Fact.create(content=content))

@agent.tool_plain(requires_approval=True)
def update_fact(fact_id: int, content: str) -> dict:
    fact = Fact.get_or_none(Fact.id == fact_id)
    if not fact:
        return {"error": "Fact not found"}
    fact.content = content
    fact.save()
    return model_to_dict(fact)

@agent.tool_plain(requires_approval=True)
def delete_fact(fact_id: int) -> dict:
    fact = Fact.get_or_none(Fact.id == fact_id)
    if not fact:
        return {"error": "Fact not found"}
    fact.delete_instance()
    return {"ok": True, "message": "Fact deleted"}

@agent.tool_plain()
def get_planned_payments() -> list[dict]:
    return list(PlannedPayment.select().dicts())

@agent.tool_plain(requires_approval=True)
def create_planned_payment(
        description: str,
        amount: float,
        currency_id: int,
        due_at: str = None,
        recurrence: str = None) -> dict:
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
    payment = PlannedPayment.get_or_none(PlannedPayment.id == payment_id)
    if not payment:
        return {"error": "Planned payment not found"}
    payment.delete_instance()
    return {"ok": True, "message": "Planned payment deleted"}

@agent.tool_plain(requires_approval=True)
def create_transaction(
        # account: int,
        amount: int,
        description: str) -> None:
    """
    Create new transaction
    Args:
        amount: product price 
        description: product description
    """
    Transaction.create(amount=amount, description=description)
