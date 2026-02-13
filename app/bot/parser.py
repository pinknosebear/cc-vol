"""Message pattern matcher and command extractor for WhatsApp bot.

Pure function layer -- no DB, no API calls, just pattern matching.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from difflib import get_close_matches
from typing import List, Optional, Union
import re


@dataclass
class ParsedCommand:
    command_type: str  # "signup", "drop", "my_shifts", "shifts", "status", "gaps", "find_sub", "help"
    args: dict


@dataclass
class ParseError:
    original: str
    suggestions: List[str] = field(default_factory=list)


# Canonical command names for fuzzy matching
COMMANDS = ["signup", "drop", "my shifts", "shifts", "status", "gaps", "find sub", "help"]

# Valid shift types
SHIFT_TYPES = {"kakad", "robe"}


def parse_date(text: str) -> Optional[date]:
    """Parse a date string into a date object.

    Supports:
    - "today" -> date.today()
    - "tomorrow" -> date.today() + 1 day
    - "2026-03-15" -> date(2026, 3, 15)
    - "15 March" or "March 15" -> date(current_year, 3, 15)
    - "15/3" or "3/15" -> try both formats (day/month first, then month/day)
    """
    text = text.strip().lower()

    if text == "today":
        return date.today()
    if text == "tomorrow":
        return date.today() + timedelta(days=1)

    # ISO format: 2026-03-15
    iso_match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", text)
    if iso_match:
        try:
            return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        except ValueError:
            return None

    # Named month formats: "15 March", "March 15", "15 Mar", "Mar 15"
    month_names = {
        "january": 1, "jan": 1,
        "february": 2, "feb": 2,
        "march": 3, "mar": 3,
        "april": 4, "apr": 4,
        "may": 5,
        "june": 6, "jun": 6,
        "july": 7, "jul": 7,
        "august": 8, "aug": 8,
        "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10,
        "november": 11, "nov": 11,
        "december": 12, "dec": 12,
    }

    # "15 March" or "15 Mar"
    dm_match = re.match(r"^(\d{1,2})\s+([a-z]+)$", text)
    if dm_match:
        day = int(dm_match.group(1))
        month_str = dm_match.group(2)
        if month_str in month_names:
            try:
                return date(date.today().year, month_names[month_str], day)
            except ValueError:
                return None

    # "March 15" or "Mar 15"
    md_match = re.match(r"^([a-z]+)\s+(\d{1,2})$", text)
    if md_match:
        month_str = md_match.group(1)
        day = int(md_match.group(2))
        if month_str in month_names:
            try:
                return date(date.today().year, month_names[month_str], day)
            except ValueError:
                return None

    # Slash formats: "15/3" or "3/15"
    slash_match = re.match(r"^(\d{1,2})/(\d{1,2})$", text)
    if slash_match:
        a, b = int(slash_match.group(1)), int(slash_match.group(2))
        year = date.today().year
        # Try day/month first
        try:
            return date(year, b, a)
        except ValueError:
            pass
        # Then month/day
        try:
            return date(year, a, b)
        except ValueError:
            return None

    return None


def _fuzzy_command(word: str) -> list[str]:
    """Return fuzzy matches for a single command word."""
    single_word_commands = ["signup", "drop", "shifts", "status", "gaps", "help"]
    matches = get_close_matches(word, single_word_commands, n=3, cutoff=0.6)
    return matches


def parse_message(text: str) -> Union[ParsedCommand, ParseError]:
    """Parse a WhatsApp message into a command."""
    original = text
    text = text.strip()
    if not text:
        return ParseError(original=original, suggestions=["help"])

    lower = text.lower()
    tokens = lower.split()

    if not tokens:
        return ParseError(original=original, suggestions=["help"])

    # --- "help" ---
    if tokens[0] == "help":
        return ParsedCommand(command_type="help", args={})

    # --- "gaps" ---
    if tokens[0] == "gaps":
        return ParsedCommand(command_type="gaps", args={})

    # --- "my shifts" ---
    if len(tokens) >= 2 and tokens[0] == "my" and tokens[1] == "shifts":
        return ParsedCommand(command_type="my_shifts", args={})

    # --- "find sub <date> <type>" ---
    if len(tokens) >= 4 and tokens[0] == "find" and tokens[1] == "sub":
        date_text = tokens[2]
        # Handle multi-word dates like "15 March"
        if len(tokens) >= 5:
            potential_date = f"{tokens[2]} {tokens[3]}"
            parsed = parse_date(potential_date)
            if parsed:
                shift_type = tokens[4].lower()
                return ParsedCommand(
                    command_type="find_sub",
                    args={"date": parsed, "type": shift_type},
                )
        parsed = parse_date(date_text)
        if parsed:
            shift_type = tokens[3].lower()
            return ParsedCommand(
                command_type="find_sub",
                args={"date": parsed, "type": shift_type},
            )
        return ParseError(original=original, suggestions=["find sub <date> <type>"])

    # --- "signup <date> <type>" ---
    if tokens[0] == "signup" and len(tokens) >= 3:
        # Try multi-word date: "signup 15 March kakad"
        if len(tokens) >= 4:
            potential_date = f"{tokens[1]} {tokens[2]}"
            parsed = parse_date(potential_date)
            if parsed:
                shift_type = tokens[3].lower()
                if shift_type in SHIFT_TYPES:
                    return ParsedCommand(
                        command_type="signup",
                        args={"date": parsed, "type": shift_type},
                    )
        parsed = parse_date(tokens[1])
        if parsed:
            shift_type = tokens[2].lower()
            if shift_type in SHIFT_TYPES:
                return ParsedCommand(
                    command_type="signup",
                    args={"date": parsed, "type": shift_type},
                )
        return ParseError(original=original, suggestions=["signup <date> kakad|robe"])

    # --- "drop <date> <type>" ---
    if tokens[0] == "drop" and len(tokens) >= 3:
        if len(tokens) >= 4:
            potential_date = f"{tokens[1]} {tokens[2]}"
            parsed = parse_date(potential_date)
            if parsed:
                shift_type = tokens[3].lower()
                if shift_type in SHIFT_TYPES:
                    return ParsedCommand(
                        command_type="drop",
                        args={"date": parsed, "type": shift_type},
                    )
        parsed = parse_date(tokens[1])
        if parsed:
            shift_type = tokens[2].lower()
            if shift_type in SHIFT_TYPES:
                return ParsedCommand(
                    command_type="drop",
                    args={"date": parsed, "type": shift_type},
                )
        return ParseError(original=original, suggestions=["drop <date> kakad|robe"])

    # --- "shifts <date>" ---
    if tokens[0] == "shifts" and len(tokens) >= 2:
        # Try multi-word date
        if len(tokens) >= 3:
            potential_date = f"{tokens[1]} {tokens[2]}"
            parsed = parse_date(potential_date)
            if parsed:
                return ParsedCommand(command_type="shifts", args={"date": parsed})
        parsed = parse_date(tokens[1])
        if parsed:
            return ParsedCommand(command_type="shifts", args={"date": parsed})
        return ParseError(original=original, suggestions=["shifts <date>"])

    # --- "status <date>" ---
    if tokens[0] == "status" and len(tokens) >= 2:
        if len(tokens) >= 3:
            potential_date = f"{tokens[1]} {tokens[2]}"
            parsed = parse_date(potential_date)
            if parsed:
                return ParsedCommand(command_type="status", args={"date": parsed})
        parsed = parse_date(tokens[1])
        if parsed:
            return ParsedCommand(command_type="status", args={"date": parsed})
        return ParseError(original=original, suggestions=["status <date>"])

    # --- Fuzzy matching for unknown commands ---
    suggestions = _fuzzy_command(tokens[0])

    # Also check two-word commands
    if len(tokens) >= 2:
        two_word = f"{tokens[0]} {tokens[1]}"
        two_word_commands = ["my shifts", "find sub"]
        two_matches = get_close_matches(two_word, two_word_commands, n=2, cutoff=0.6)
        suggestions.extend(two_matches)

    return ParseError(original=original, suggestions=suggestions)
