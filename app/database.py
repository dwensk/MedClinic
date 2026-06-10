"""
Инициализация подключения к базе данных (SQLAlchemy 2.0, синхронный режим).

Здесь создаётся:
- engine        — движок подключения к БД;
- SessionLocal  — фабрика сессий;
- Base          — базовый класс для всех ORM-моделей;
- get_db()      — зависимость (dependency) FastAPI для выдачи сессии в роутах.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

# SQLite требует особый аргумент для работы в многопоточном FastAPI.
# Для PostgreSQL дополнительные аргументы не нужны.
connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,          # в режиме отладки печатает SQL-запросы
    connect_args=connect_args,
    pool_pre_ping=True,           # проверяет «живость» соединения перед запросом
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Базовый класс для декларативных ORM-моделей."""
    pass


def get_db():
    """
    Зависимость FastAPI: открывает сессию на время запроса
    и гарантированно закрывает её после ответа.

    Пример использования в роуте:
        def read_patients(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
