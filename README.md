# Closer

Telegram-бот для заключения договоров между людьми и компаниями: описал сделку — бот собрал договор из шаблона юриста — обе стороны подписали кодом из СМС.

- `CURSOR_PROMPT.md` — с чего начать разработку в Cursor (промты по этапам).
- `docs/spec.md` — ТЗ.
- `docs/pep_offer.md` — соглашение о простой электронной подписи.
- `templates/` — шаблоны договоров автора и описание полей.
- `closer/documents/` — заполнение шаблонов и PDF (уже работает).

Быстрая проверка: `pip install lxml pytest && pytest && python tools/fill_example.py` (нужен LibreOffice).
