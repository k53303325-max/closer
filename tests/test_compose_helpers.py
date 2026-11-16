from closer.bot.handlers.compose import _deal_missing_fields
from closer.services.normalize import format_price_rub, parse_price


def test_deal_missing_all():
    assert _deal_missing_fields({}) == ["services", "term", "price", "payment"]


def test_deal_complete():
    deal = {"services": "x", "term": "до 01.01.2027", "price": 45000, "payment": "prepay"}
    assert _deal_missing_fields(deal) == []


def test_price_parse():
    assert parse_price("45 000") == 45000
    assert format_price_rub(45000) == "45 000"