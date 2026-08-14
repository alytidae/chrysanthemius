import telebot
import json
import uuid
import os
from agent import agent
from pydantic_ai import DeferredToolRequests
import logging
from models import Message
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    UserPromptPart,
    TextPart,
)

logger = logging.getLogger(__name__)

PREVIOUS_MESSAGES_COUNT = 0

pending_approvals = {}
token = os.getenv("TELEGRAM_BOT_TOKEN")

if not token:
    raise RuntimeError(
        "Variable TELEGRAM_BOT_TOKEN is not found .env"
    )

bot = telebot.TeleBot(token)

# def format_approvals(approvals):
#     products = "hello"
#
#     # for approval in approvals:
#     #     args = json.loads(approval.args)
#     #     products += f"- {args['description']} - {args['amount']}\n"
#     #
    # return products
    #

@bot.message_handler(commands=["help"])
def handle_command(message):
    bot.reply_to(message, 
    """
    /get_memory_count - Gives how many previous messages agents remember
    /clean_memory - Set previous message count to 0
    """)

@bot.message_handler(commands=["get_memory_count"])
def get_memory_count(message):
    bot.reply_to(message, f"Agent remembers {PREVIOUS_MESSAGES_COUNT} previous messages")

@bot.message_handler(commands=["clean_memory"])
def clean_memory(message):
    global PREVIOUS_MESSAGES_COUNT
    PREVIOUS_MESSAGES_COUNT = 0
    bot.reply_to(message, f"Agent remembers 0 previous messages")

@bot.message_handler(content_types=["text"], chat_types=["private"])
def handle_text(message: telebot.types.Message) -> None:
    global PREVIOUS_MESSAGES_COUNT

    if str(message.from_user.id) != os.getenv("ALLOWED_TELEGRAM_USER_ID"):
        return

    history = []
    for history_message in (
        Message
        .select()
        .order_by(Message.created_at.desc())
        .limit(PREVIOUS_MESSAGES_COUNT)[::-1]
    ):
        if history_message.role == "user":
            history.append(
                ModelRequest(
                    parts=[UserPromptPart(content=history_message.content)]
                )
            )

        elif history_message.role == "assistant":
            history.append(
                ModelResponse(
                    parts=[TextPart(content=history_message.content)]
                )
            )

    Message.create(role="user", content=message.text)

    result = agent.run_sync(
        message.text,
        message_history=history
    )

    Message.create(role="assistant", content=result.output)

    PREVIOUS_MESSAGES_COUNT += 2
    if PREVIOUS_MESSAGES_COUNT > 20:
        PREVIOUS_MESSAGES_COUNT = 20

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
        bot.send_rich_message(
            chat_id=message.chat.id,
            rich_message=telebot.types.InputRichMessage(
                markdown=str(result.output),
            ),
            reply_parameters=telebot.types.ReplyParameters(
                message_id=message.message_id,
            ),
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
    if str(call.from_user.id) != os.getenv("ALLOWED_TELEGRAM_USER_ID"):
        return

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
        text=f"{call.message.rich_message}\n\n{status}",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )

def run_telegram_bot():
    logger.info("Telegram bot started")
    bot.infinity_polling(skip_pending=True)

