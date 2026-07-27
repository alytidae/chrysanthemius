import telebot
import json
import uuid
import os
from agent import agent
from pydantic_ai import DeferredToolRequests
import logging

logger = logging.getLogger(__name__)

pending_approvals = {}
token = os.getenv("TELEGRAM_BOT_TOKEN")

if not token:
    raise RuntimeError(
        "Variable TELEGRAM_BOT_TOKEN is not found .env"
    )

bot = telebot.TeleBot(token)

def format_approvals(approvals):
    products = ""

    for approval in approvals:
        args = json.loads(approval.args)
        products += f"- {args['description']} - {args['amount']}\n"

    return products


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
        bot.send_rich_message(
            chat_id=message.chat.id,
            rich_message=telebot.types.InputRichMessage(
                markdown=format_approvals(result.output.approvals),
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

def run_telegram_bot():
    logger.info("Telegram bot started")
    bot.infinity_polling(skip_pending=True)

