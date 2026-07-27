import datetime
import os
from peewee import *
from pydantic_ai import Agent, DeferredToolRequests
from dotenv import load_dotenv
import telebot
import uuid

load_dotenv()

db = SqliteDatabase('database.db')

pending_approvals = {}

token = os.getenv("TELEGRAM_BOT_TOKEN")

if not token:
    raise RuntimeError(
        "Variable TELEGRAM_BOT_TOKEN is not found .env"
    )

bot = telebot.TeleBot(token)

class BaseModel(Model):
    class Meta:
        database = db

class Transaction(BaseModel):
    amount = DecimalField()
    description = TextField()
    timestamp = DateTimeField(default=datetime.datetime.now)

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

@agent.tool_plain(requires_approval=True)
def create_transaction(amount: int, description: str) -> bool:
    """
    Create new transaction
    Args:
        amount: product price 
        description: product description
    """
    Transaction.create(amount=amount, description=description)

@agent.tool_plain
def get_stats() -> float:
    """
    Get spending statistic
    """
    return Transaction.select(fn.SUM(Transaction.amount)).scalar()

@bot.message_handler(content_types=["text"], chat_types=["private"])
def handle_text(message: telebot.types.Message) -> None:
    if str(message.from_user.id) != os.getenv("ALLOWED_TELEGRAM_USER_ID"):
        return

    result = agent.run_sync(message.text)
    if isinstance(result.output, DeferredToolRequests):
        keyboard = telebot.types.InlineKeyboardMarkup()

        callback_id = uuid.uuid4().hex

        pending_approvals[callback_id] = {
            "requests": result.output,
            "messages": result.all_messages(),
        }
        
        keyboard.row(
            telebot.types.InlineKeyboardButton(
                text="✅ Approve",
                callback_data=f"approve:{callback_id}",
            ),
            telebot.types.InlineKeyboardButton(
                text="❌ Deny",
                callback_data=f"deny:{callback_id}",
            ),
        )
        bot.reply_to(
            message=message,
            text="Need approval",
            reply_markup=keyboard,
        )
    else:
        bot.send_rich_message(
            chat_id=message.chat.id,
            rich_message=telebot.types.InputRichMessage(
                markdown=str(result.output),
            ),
            reply_parameters=telebot.types.ReplyParameters(
                message_id=message.message_id,
            ),
        )

@bot.callback_query_handler(
    func=lambda call: call.data.startswith(("approve:", "deny:"))
)
def handle_approval(call):
    action, approval_id = call.data.split(":", maxsplit=1)

    try:
        approval = pending_approvals.pop(approval_id)
    except KeyError:
        return 
    
    if action == "approve":
        status = "✅ Approve"

        requests = approval["requests"]
        messages = approval["messages"]

        decisions = {}

        for tool_call in requests.approvals:
            decisions[tool_call.tool_call_id] = True

        deferred_results = requests.build_results(
            approvals=decisions
        )

        deferred_results = requests.build_results(
            approvals=decisions
        )

        final_result = agent.run_sync(
            message_history=messages,
            deferred_tool_results=deferred_results,
        )

        bot.send_rich_message(
            chat_id=call.message.chat.id,
            rich_message=telebot.types.InputRichMessage(
                markdown=str(final_result.output),
            ),
        )
    else:
        status = "❌ Deny"

    bot.answer_callback_query(
        callback_query_id=call.id,
        text=status,
    )
    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=None,
    )
    bot.edit_message_text(
        text=f"{call.message.text}\n\n{status}",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )


def main():
    db.connect()
    db.create_tables([Transaction])

    bot.infinity_polling(skip_pending=True)

if __name__ == "__main__":
    main()
