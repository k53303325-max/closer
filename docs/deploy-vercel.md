# Тестовый деплой на Vercel

На Vercel только **webhook** (не polling). Нужны внешние **PostgreSQL** и **Redis** (Neon + Upstash).

## Переменные Vercel

`BOT_TOKEN`, `DATABASE_URL` (`postgresql+asyncpg://...`), `REDIS_URL`, `PD_ENCRYPTION_KEY`, `WEBHOOK_URL` (`https://<project>.vercel.app`), `SETUP_SECRET`, `SMS_PROVIDER=fake`, `ADMIN_TG_USERNAMES`.

Миграции: `alembic upgrade head` с тем же `DATABASE_URL`.

## После деплоя

`GET https://<project>.vercel.app/api/telegram?setup=1&secret=<SETUP_SECRET>`
