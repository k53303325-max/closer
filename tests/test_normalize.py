from datetime import date

from closer.services.normalize import format_price_rub, normalize_term, parse_price


def test_format_price():
    assert format_price_rub(45000) == "45 000"


def test_parse_price():
    assert parse_price("45 000 руб") == 45000


def test_normalize_term_until():
    base = date(2026, 11, 1)
    assert normalize_term("до 30.11.2026", base).startswith("до ")


def test_normalize_weeks():
    base = date(2026, 11, 1)
    got = normalize_term("3 недели", base)
    assert got.startswith("до ")
