# МедКлиник — Дәрігерге жазылу жүйесі

Внутренняя корпоративная система записи к врачу и управления клиникой.

**Стек:** Python · FastAPI · PostgreSQL · SQLAlchemy 2.0 · Pydantic v2 · Docker

---

## Возможности (по фазам)

| Фаза | Неделя | Содержание |
|------|--------|------------|
| 1 | 1–2 | Архитектура БД (7 таблиц), структура проекта, конфигурация |
| 2 | 2 | ORM-модели, подключение к БД, сидинг тестовых данных |
| 3 | 3 | Pydantic-схемы, валидация (ИИН, телефон, дата приёма) |
| 4+ | 4–7 | CRUD-роуты, авторизация, тесты, деплой |

## Структура проекта

## Структура проекта

```
MedClinic/
├── app/
│   ├── main.py              # точка входа FastAPI, подключение роутеров
│   ├── config.py            # настройки из .env
│   ├── database.py          # engine и сессии SQLAlchemy
│   ├── auth.py              # JWT-авторизация, хэширование паролей
│   ├── enums.py             # роли и статусы (Enum)
│   ├── models.py            # ORM-модели (7 таблиц)
│   ├── schemas.py           # Pydantic-схемы запросов/ответов
│   ├── validators.py        # валидация ИИН, телефона, даты
│   ├── seed.py              # тестовые данные (Faker)
│   ├── routers/             # CRUD-эндпоинты
│   │   ├── patients.py      #   пациенты
│   │   ├── doctors.py       #   врачи
│   │   ├── departments.py   #   отделения
│   │   └── appointments.py  #   записи на приём
│   └── static/              # веб-интерфейс (HTML/CSS/JS)
├── tests/                   # pytest-тесты (93 теста)
│   ├── conftest.py          # фикстуры, тестовая БД
│   └── test_*.py            # тесты по модулям
├── schema.sql               # DDL-схема БД (PostgreSQL)
├── medklinik_erd.png        # ER-диаграмма
├── .env.example             # шаблон переменных окружения
├── Dockerfile               # образ приложения
└── docker-compose.yml       # запуск api + PostgreSQL
```
```

## Запуск — вариант A: локально (SQLite, быстрый старт)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# В .env оставьте строку с DATABASE_URL=sqlite:///./medklinik.db

python -m app.seed                 # наполнить тестовыми данными
uvicorn app.main:app --reload
```

Откройте Swagger: <http://localhost:8000/docs>

## Запуск — вариант B: Docker (PostgreSQL, как в продакшене)

```bash
docker compose up --build
# После старта контейнеров:
docker compose exec api python -m app.seed
```

## Тесты

```bash
pip install pytest
pytest -q
```

## Тестовые учётные данные (после сидинга)

| Роль | Email | Пароль |
|------|-------|--------|
| Администратор | `admin@medklinik.kz` | `admin12345` |
| Врачи | случайные email из лога сидинга | `doctor12345` |

## Что доработать на Неделе 4+

- **Хэширование паролей:** заменить `_fake_hash` в `seed.py` на `passlib`/`bcrypt`.
- **Миграции:** подключить **Alembic** вместо `Base.metadata.create_all`.
- **CRUD-роуты:** реализовать в `app/routers/`, подключить в `main.py`.
- **Авторизация:** JWT-токены (роли admin/doctor), `SECRET_KEY` из `.env`.
- **ИИН с контрольным разрядом:** в `validators.py` есть готовая функция `validate_iin_checksum`.
