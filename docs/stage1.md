# Этап 1 — проверка

## Запуск (polling)

1. Снять webhook (если был): в браузере  
   `https://api.telegram.org/bot<TOKEN>/deleteWebhook`  
   или `curl` с вашим `BOT_TOKEN`.

2. Остановить `tools/minimal_poller.py`, если запущен.

3. Из корня проекта:

```bash
docker compose up --build bot
```

Локально (Python 3.12 + зависимости из `pyproject.toml`):

```bash
pip install -e ".[dev]"
python -m closer.bot
```

## Профиль бота (описания + команды)

```bash
python tools/setup_telegram_profile.py
```

Тексты берутся из `texts/ru.yaml` (блок `bot`).

Фото: @BotFather — `brand/avatar.png`, `brand/cover.png`.

## Чеклист в Telegram

| Проверка | Ожидание |
|---|---|
| Профиль бота | Короткое описание из п.2 ТЗ |
| Пустой чат до Start | Длинное описание из п.3 |
| Меню команд | 5 команд без verify |
| `/start` | Текст из п.5 |
| `/help` | 3–4 строки из `help.text` |
| `/new`, `/my`, `/profile` | «Скоро будет.» |
| Любой другой текст | «Пока я умею только команды из меню.» |
