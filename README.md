# tg_courier

Telegram-бот для логирования смен курьеров.

## Возможности

- старт и завершение смены
- добавление заказов
- личная статистика
- summary после закрытия смены
- basic и advanced режимы
- multi-tenant схема через `account_id`

## Стек

- Python 3.11+
- aiogram 3
- Supabase REST API
- Open-Meteo API для погоды

## Локальный запуск

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

Скопируйте `.env.example` в `.env` и заполните реальные значения.

## Render

Текущий бот работает через Telegram long polling, поэтому на Render его нужно запускать как Background Worker, а не как Web Service. Для Blueprint-деплоя используйте `render.yaml`.

Если создаете сервис вручную:

- Service type: `Background Worker`
- Build command: `pip install -r requirements.txt`
- Start command: `python -m app.main`
- Python version: `3.11.11`

## Переменные окружения

- `BOT_TOKEN` - токен Telegram-бота
- `SUPABASE_URL` - URL проекта Supabase
- `SUPABASE_KEY` - Supabase `service_role` key
- `SUPABASE_TIMEOUT_SECONDS` - timeout HTTP-запросов к Supabase
- `DEFAULT_CITY` - город для weather snapshot
- `DEFAULT_ACCOUNT_SLUG` - slug default tenant, по умолчанию `default-account`
- `WEATHER_LAT` - широта города для погоды
- `WEATHER_LON` - долгота города для погоды
- `WEATHER_TIMEZONE` - IANA timezone для weather API, например `Europe/Belgrade`
- `PYTHON_VERSION` - версия Python для Render

Реальные значения для copy-paste лежат в локальном файле `render-env.copy-paste.txt`. Этот файл добавлен в `.gitignore` и не должен попадать на GitHub.

## Миграции

Перед запуском примените миграции в Supabase SQL Editor по порядку:

1. `migrations/001_init.sql`
2. `migrations/002_advanced_research.sql`
3. `migrations/003_multi_tenant.txt`
4. `migrations/004_drop_legacy_shift_time_not_null.txt`
5. `migrations/005_fill_legacy_columns_in_rpc.txt`
