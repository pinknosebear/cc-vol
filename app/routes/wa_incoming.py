"""WhatsApp incoming message endpoint.

Receives messages from the WA bridge and dispatches to the correct handler.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.bot.auth import get_volunteer_context
from app.bot.parser import parse_message, ParsedCommand, ParseError
from app.bot.handlers.vol_signup import handle_signup
from app.bot.handlers.vol_drop import handle_drop
from app.bot.handlers.vol_query import handle_my_shifts, handle_shifts
from app.bot.handlers.coordinator import handle_status, handle_gaps, handle_find_sub

router = APIRouter(tags=["whatsapp"])

COORDINATOR_COMMANDS = {"status", "gaps", "find_sub"}

HELP_TEXT = (
    "Available commands:\n"
    "- signup <date> kakad|robe\n"
    "- drop <date> kakad|robe\n"
    "- my shifts\n"
    "- shifts <date>\n"
    "- help\n"
    "\n"
    "Coordinator commands:\n"
    "- status <date>\n"
    "- gaps\n"
    "- find sub <date> kakad|robe"
)

HANDLERS = {
    "signup": handle_signup,
    "drop": handle_drop,
    "my_shifts": handle_my_shifts,
    "shifts": handle_shifts,
    "status": handle_status,
    "gaps": handle_gaps,
    "find_sub": handle_find_sub,
}


class IncomingMessage(BaseModel):
    phone: str
    message: str


@router.post("/api/wa/incoming")
def wa_incoming(body: IncomingMessage, request: Request):
    db = request.app.state.db

    # 1. Auth: look up volunteer by phone
    context = get_volunteer_context(db, body.phone)
    if context is None:
        return {"reply": "Phone not registered."}

    # 2. Parse the message
    parsed = parse_message(body.message)
    if isinstance(parsed, ParseError):
        suggestions = ", ".join(parsed.suggestions) if parsed.suggestions else "help"
        return {"reply": f"I didn't understand that. Did you mean: {suggestions}?"}

    # 3. Check coordinator-only commands
    if parsed.command_type in COORDINATOR_COMMANDS and not context.is_coordinator:
        return {"reply": "That command is for coordinators only."}

    # 4. Route to handler
    if parsed.command_type == "help":
        return {"reply": HELP_TEXT}

    handler = HANDLERS.get(parsed.command_type)
    if handler is None:
        return {"reply": "Unknown command. Send 'help' for a list of commands."}

    result = handler(db, context, parsed.args)
    return {"reply": result}
