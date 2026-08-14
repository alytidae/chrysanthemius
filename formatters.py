import json
from typing import Any, Callable

from models import Account, Category, Currency, Fact, PlannedPayment, Transaction
from pydantic_ai import DeferredToolRequests
from pydantic_ai.messages import ToolCallPart


def _parse_args(part: ToolCallPart) -> dict[str, Any]:
    if isinstance(part.args, dict):
        return part.args
    if isinstance(part.args, str):
        try:
            return json.loads(part.args)
        except json.JSONDecodeError:
            return {}
    return {}


def _fmt_amount(value: Any) -> str:
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def _resolve_account(account_id: Any) -> str:
    try:
        account = Account.get_by_id(account_id)
    except (Account.DoesNotExist, ValueError, TypeError):
        return f"id {account_id}"
    return f'"{account.name}" (id {account_id})'


def _currency_code(currency_id: Any) -> str:
    try:
        return Currency.get_by_id(currency_id).code
    except (Currency.DoesNotExist, ValueError, TypeError):
        return f"id {currency_id}"


def _resolve_category(category_id: Any) -> str:
    try:
        category = Category.get_by_id(category_id)
    except (Category.DoesNotExist, ValueError, TypeError):
        return f"id {category_id}"
    return f'"{category.name}" (id {category_id})'


def _resolve_transaction(transaction_id: Any) -> str:
    try:
        transaction = Transaction.get_by_id(transaction_id)
    except (Transaction.DoesNotExist, ValueError, TypeError):
        return f"id {transaction_id}"
    label = transaction.description or f"{transaction.transaction_type}"
    return f'"{label}" (id {transaction_id})'


def _resolve_payment(payment_id: Any) -> str:
    try:
        payment = PlannedPayment.get_by_id(payment_id)
    except (PlannedPayment.DoesNotExist, ValueError, TypeError):
        return f"id {payment_id}"
    return f'"{payment.description}" (id {payment_id})'


def _resolve_fact(fact_id: Any) -> str:
    try:
        fact = Fact.get_by_id(fact_id)
    except (Fact.DoesNotExist, ValueError, TypeError):
        return f"id {fact_id}"
    excerpt = fact.content if len(fact.content) <= 50 else fact.content[:47] + "..."
    return f'"{excerpt}" (id {fact_id})'


def _render_create_account(args: dict[str, Any]) -> str:
    return f'Create account "{args.get("name")}"'


def _render_update_account(args: dict[str, Any]) -> str:
    changes = []
    if args.get("name") is not None:
        changes.append(f'name: "{args["name"]}"')
    if args.get("description") is not None:
        changes.append(f'description: "{args["description"]}"')
    text = f'Update account {_resolve_account(args.get("account_id"))}'
    if changes:
        text += f" ({', '.join(changes)})"
    return text


def _render_delete_account(args: dict[str, Any]) -> str:
    return f'Delete account {_resolve_account(args.get("account_id"))}'


def _render_create_currency(args: dict[str, Any]) -> str:
    return f'Create currency "{args.get("code")}"'


def _render_update_currency(args: dict[str, Any]) -> str:
    text = f'Update currency {_currency_code(args.get("currency_id"))}'
    if args.get("code") is not None:
        text += f' (code: "{args["code"]}")'
    return text


def _render_delete_currency(args: dict[str, Any]) -> str:
    return f'Delete currency {_currency_code(args.get("currency_id"))}'


def _render_create_category(args: dict[str, Any]) -> str:
    return f'Create category "{args.get("name")}"'


def _render_update_category(args: dict[str, Any]) -> str:
    text = f'Update category {_resolve_category(args.get("category_id"))}'
    if args.get("name") is not None:
        text += f' (name: "{args["name"]}")'
    return text


def _render_delete_category(args: dict[str, Any]) -> str:
    return f'Delete category {_resolve_category(args.get("category_id"))}'


def _render_create_fact(args: dict[str, Any]) -> str:
    return f'Create fact "{args.get("content")}"'


def _render_update_fact(args: dict[str, Any]) -> str:
    text = f"Update fact {_resolve_fact(args.get('fact_id'))}"
    if args.get("content") is not None:
        text += f' (content: "{args["content"]}")'
    return text


def _render_delete_fact(args: dict[str, Any]) -> str:
    return f"Delete fact {_resolve_fact(args.get('fact_id'))}"


def _render_create_planned_payment(args: dict[str, Any]) -> str:
    text = (
        f'Create planned payment "{args.get("description")}" '
        f'— {_fmt_amount(args.get("amount"))} {_currency_code(args.get("currency_id"))}'
    )
    if args.get("due_at"):
        text += f' (due: {args["due_at"]})'
    if args.get("recurrence"):
        text += f' ({args["recurrence"]})'
    return text


def _render_update_planned_payment(args: dict[str, Any]) -> str:
    changes = []
    if args.get("description") is not None:
        changes.append(f'description: "{args["description"]}"')
    if args.get("amount") is not None:
        changes.append(f"amount: {_fmt_amount(args['amount'])}")
    if args.get("currency_id") is not None:
        changes.append(f"currency: {_currency_code(args['currency_id'])}")
    if args.get("due_at") is not None:
        changes.append(f'due: {args["due_at"]}')
    if args.get("recurrence") is not None:
        changes.append(f'recurrence: {args["recurrence"]}')
    text = f'Update planned payment {_resolve_payment(args.get("payment_id"))}'
    if changes:
        text += f" ({', '.join(changes)})"
    return text


def _render_delete_planned_payment(args: dict[str, Any]) -> str:
    return f'Delete planned payment {_resolve_payment(args.get("payment_id"))}'


def _render_create_transaction(args: dict[str, Any]) -> str:
    text = (
        f'Create {args.get("transaction_type")} '
        f'{_fmt_amount(args.get("amount"))} {_currency_code(args.get("currency_id"))} '
        f'on {_resolve_account(args.get("account_id"))}'
    )
    if args.get("description"):
        text += f' — "{args["description"]}"'
    if args.get("category_id") is not None:
        text += f' — category {_resolve_category(args["category_id"])}'
    if args.get("occurred_at_str"):
        text += f' ({args["occurred_at_str"]})'
    return text


def _render_update_transaction(args: dict[str, Any]) -> str:
    changes = []
    if args.get("account_id") is not None:
        changes.append(f'on {_resolve_account(args["account_id"])}')
    if args.get("amount") is not None:
        changes.append(f"amount: {_fmt_amount(args['amount'])}")
    if args.get("currency_id") is not None:
        changes.append(f"currency: {_currency_code(args['currency_id'])}")
    if args.get("transaction_type") is not None:
        changes.append(f'type: {args["transaction_type"]}')
    if args.get("category_id") is not None:
        changes.append(f"category: {_resolve_category(args['category_id'])}")
    if args.get("description") is not None:
        changes.append(f'description: "{args["description"]}"')
    if args.get("occurred_at_str"):
        changes.append(f'date: {args["occurred_at_str"]}')
    text = f"Update transaction {_resolve_transaction(args.get('transaction_id'))}"
    if changes:
        text += f" ({', '.join(changes)})"
    return text


def _render_delete_transaction(args: dict[str, Any]) -> str:
    return f"Delete transaction {_resolve_transaction(args.get('transaction_id'))}"


def _render_fallback(tool_name: str, args: dict[str, Any]) -> str:
    text = f"Call tool {tool_name}"
    if args:
        text += "\n```json\n" + json.dumps(args, indent=2) + "\n```"
    return text


TOOL_RENDERERS: dict[str, Callable[[dict[str, Any]], str]] = {
    "create_account": _render_create_account,
    "update_account": _render_update_account,
    "delete_account": _render_delete_account,
    "create_currency": _render_create_currency,
    "update_currency": _render_update_currency,
    "delete_currency": _render_delete_currency,
    "create_category": _render_create_category,
    "update_category": _render_update_category,
    "delete_category": _render_delete_category,
    "create_fact": _render_create_fact,
    "update_fact": _render_update_fact,
    "delete_fact": _render_delete_fact,
    "create_planned_payment": _render_create_planned_payment,
    "update_planned_payment": _render_update_planned_payment,
    "delete_planned_payment": _render_delete_planned_payment,
    "create_transaction": _render_create_transaction,
    "update_transaction": _render_update_transaction,
    "delete_transaction": _render_delete_transaction,
}


def format_deferred_requests(requests: DeferredToolRequests) -> str:
    lines = ["Approval required", ""]
    for index, part in enumerate(requests.approvals, start=1):
        renderer = TOOL_RENDERERS.get(part.tool_name, _render_fallback)
        args = _parse_args(part)
        if part.tool_name in TOOL_RENDERERS:
            rendered = renderer(args)
        else:
            rendered = renderer(part.tool_name, args)
        rendered = rendered.replace("\n", "\n   ")
        lines.append(f"{index}. {rendered}")
    lines.extend(["", "Approve all or deny below:"])
    return "\n".join(lines)