"""Tests for app.bot.parser — message pattern matcher and command extractor."""

from datetime import date, timedelta

import pytest

from app.bot.parser import ParsedCommand, ParseError, parse_date, parse_message


# ---------- parse_date ----------


class TestParseDate:
    def test_today(self):
        assert parse_date("today") == date.today()

    def test_tomorrow(self):
        assert parse_date("tomorrow") == date.today() + timedelta(days=1)

    def test_iso_format(self):
        assert parse_date("2026-03-15") == date(2026, 3, 15)

    def test_day_month_name(self):
        result = parse_date("15 March")
        assert result == date(date.today().year, 3, 15)

    def test_month_name_day(self):
        result = parse_date("March 15")
        assert result == date(date.today().year, 3, 15)

    def test_short_month(self):
        result = parse_date("15 Mar")
        assert result == date(date.today().year, 3, 15)

    def test_slash_day_month(self):
        # 15/3 -> March 15
        result = parse_date("15/3")
        assert result == date(date.today().year, 3, 15)

    def test_slash_month_day(self):
        # 3/15 -> March 15 (day/month fails because month=15 invalid, falls back to month/day)
        result = parse_date("3/15")
        assert result == date(date.today().year, 3, 15)

    def test_invalid(self):
        assert parse_date("not-a-date") is None

    def test_case_insensitive(self):
        assert parse_date("TODAY") == date.today()
        assert parse_date("Tomorrow") == date.today() + timedelta(days=1)


# ---------- parse_message: valid commands ----------


class TestParseMessageValid:
    def test_signup_iso(self):
        result = parse_message("signup 2026-03-15 kakad")
        assert isinstance(result, ParsedCommand)
        assert result.command_type == "signup"
        assert result.args["date"] == date(2026, 3, 15)
        assert result.args["type"] == "kakad"

    def test_signup_robe(self):
        result = parse_message("signup 2026-03-15 robe")
        assert isinstance(result, ParsedCommand)
        assert result.command_type == "signup"
        assert result.args["type"] == "robe"

    def test_drop(self):
        result = parse_message("drop 2026-03-15 robe")
        assert isinstance(result, ParsedCommand)
        assert result.command_type == "drop"
        assert result.args["date"] == date(2026, 3, 15)
        assert result.args["type"] == "robe"

    def test_my_shifts(self):
        result = parse_message("my shifts")
        assert isinstance(result, ParsedCommand)
        assert result.command_type == "my_shifts"
        assert result.args == {}

    def test_shifts_date(self):
        result = parse_message("shifts 2026-03-15")
        assert isinstance(result, ParsedCommand)
        assert result.command_type == "shifts"
        assert result.args["date"] == date(2026, 3, 15)

    def test_status_date(self):
        result = parse_message("status 2026-03-15")
        assert isinstance(result, ParsedCommand)
        assert result.command_type == "status"
        assert result.args["date"] == date(2026, 3, 15)

    def test_gaps(self):
        result = parse_message("gaps")
        assert isinstance(result, ParsedCommand)
        assert result.command_type == "gaps"
        assert result.args == {}

    def test_find_sub(self):
        result = parse_message("find sub 2026-03-15 kakad")
        assert isinstance(result, ParsedCommand)
        assert result.command_type == "find_sub"
        assert result.args["date"] == date(2026, 3, 15)
        assert result.args["type"] == "kakad"

    def test_help(self):
        result = parse_message("help")
        assert isinstance(result, ParsedCommand)
        assert result.command_type == "help"
        assert result.args == {}


# ---------- case insensitivity ----------


class TestCaseInsensitive:
    def test_signup_upper(self):
        result = parse_message("SIGNUP 2026-03-15 kakad")
        assert isinstance(result, ParsedCommand)
        assert result.command_type == "signup"

    def test_drop_mixed(self):
        result = parse_message("Drop 2026-03-15 Robe")
        assert isinstance(result, ParsedCommand)
        assert result.command_type == "drop"
        assert result.args["type"] == "robe"

    def test_my_shifts_upper(self):
        result = parse_message("MY SHIFTS")
        assert isinstance(result, ParsedCommand)
        assert result.command_type == "my_shifts"

    def test_help_upper(self):
        result = parse_message("HELP")
        assert isinstance(result, ParsedCommand)
        assert result.command_type == "help"


# ---------- date format variants ----------


class TestDateFormats:
    def test_signup_today(self):
        result = parse_message("signup today kakad")
        assert isinstance(result, ParsedCommand)
        assert result.args["date"] == date.today()

    def test_signup_tomorrow(self):
        result = parse_message("signup tomorrow robe")
        assert isinstance(result, ParsedCommand)
        assert result.args["date"] == date.today() + timedelta(days=1)

    def test_signup_named_month(self):
        result = parse_message("signup 15 March kakad")
        assert isinstance(result, ParsedCommand)
        assert result.args["date"] == date(date.today().year, 3, 15)

    def test_shifts_named_month(self):
        result = parse_message("shifts 15 March")
        assert isinstance(result, ParsedCommand)
        assert result.args["date"] == date(date.today().year, 3, 15)


# ---------- fuzzy matching / errors ----------


class TestParseErrors:
    def test_typo_singup(self):
        result = parse_message("singup 2026-03-15 kakad")
        assert isinstance(result, ParseError)
        assert "signup" in result.suggestions

    def test_typo_drp(self):
        result = parse_message("drp 2026-03-15 robe")
        assert isinstance(result, ParseError)
        assert "drop" in result.suggestions

    def test_gibberish(self):
        result = parse_message("blah blah")
        assert isinstance(result, ParseError)

    def test_empty_string(self):
        result = parse_message("")
        assert isinstance(result, ParseError)

    def test_whitespace_only(self):
        result = parse_message("   ")
        assert isinstance(result, ParseError)
