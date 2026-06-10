"""
Конфигурация приложения.

Все настройки читаются из переменных окружения (файл .env).
pydantic-settings автоматически валидирует типы и подставляет значения.
"""

import warnings

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Строка подключения к БД.
    # Продакшен (основной стек): PostgreSQL.
    # Для локальной разработки можно временно использовать SQLite (см. .env.example).
    DATABASE_URL: str = "sqlite:///./medklinik.db"

    APP_NAME: str = "МедКлиник API"
    DEBUG: bool = True

    # Секрет для JWT-авторизации.
    SECRET_KEY: str = "change-me-in-production"

    # Пароли для начального сидинга — переопределяйте через .env в продакшене.
    ADMIN_PASSWORD: str = "admin12345"
    DOCTOR_PASSWORD: str = "doctor12345"

    @model_validator(mode="after")
    def _check_secret_key(self) -> "Settings":
        if not self.DEBUG and self.SECRET_KEY == "change-me-in-production":
            warnings.warn(
                "SECRET_KEY не изменён (используется значение по умолчанию 'change-me-in-production'). "
                "Установите безопасный секрет в переменной окружения SECRET_KEY.",
                stacklevel=2,
            )
        return self


# Единый экземпляр настроек, импортируется во всём приложении.
settings = Settings()
