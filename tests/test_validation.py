from closer.services.validation import (
    validate_inn,
    validate_ogrn,
    validate_ogrnip,
    validate_passport,
)


def test_passport_ok():
    assert validate_passport("4510 123456")


def test_inn_10():
    assert validate_inn("7707083893")


def test_ogrn():
    assert validate_ogrn("1027700132195")


def test_ogrnip():
    assert validate_ogrnip("304500116000157")
