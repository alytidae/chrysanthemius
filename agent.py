from pydantic_ai import Agent, DeferredToolRequests
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
        Account.create(name, description)
    )
    
@agent.tool_plain()
def get_currencies() -> list[dict]:
    return list(Currency.select().dicts())

@agent.tool_plain()
def get_categories() -> list[dict]:
    return list(Category.select().dicts())

@agent.tool_plain()
def get_facts() -> list[dict]:
    return list(Fact.select().dicts())

@agent.tool_plain()
def get_planned_payments() -> list[dict]:
    return list(PlannedPayment.select().dicts())

@agent.tool_plain(requires_approval=True)
def create_transaction(
        # account: int,
        amount: int
        , description: str) -> None:
    """
    Create new transaction
    Args:
        amount: product price 
        description: product description
    """
    Transaction.create(amount=amount, description=description)
