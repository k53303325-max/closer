from __future__ import annotations

import re


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def validate_inn(value: str) -> bool:
    inn = _digits(value)
    if len(inn) not in (10, 12):
        return False
    if len(inn) == 10:
        coeffs = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        s = sum(int(inn[i]) * coeffs[i] for i in range(9)) % 11 % 10
        return s == int(inn[9])
    coeffs1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    coeffs2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    c1 = sum(int(inn[i]) * coeffs1[i] for i in range(10)) % 11 % 10
    c2 = sum(int(inn[i]) * coeffs2[i] for i in range(11)) % 11 % 10
    return c1 == int(inn[10]) and c2 == int(inn[11])


def validate_ogrn(value: str) -> bool:
    ogrn = _digits(value)
    if len(ogrn) != 13:
        return False
    tail = int(ogrn[:-1]) % 11 % 10
    return tail == int(ogrn[-1])


def validate_ogrnip(value: str) -> bool:
    ogrnip = _digits(value)
    if len(ogrnip) != 15:
        return False
    tail = int(ogrnip[:-1]) % 13 % 10
    return tail == int(ogrnip[-1])


def validate_passport(value: str) -> bool:
    d = _digits(value)
    if len(d) != 10:
        return False
    series, number = d[:4], d[4:]
    return series.isdigit() and number.isdigit()


def format_passport(value: str) -> str:
    d = _digits(value)
    if len(d) != 10:
        raise ValueError("passport must be 4+6 digits")
    return f"{d[:4]} {d[4:]}"
