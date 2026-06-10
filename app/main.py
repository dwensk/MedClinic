"""
Точка входа FastAPI-приложения.

Запуск (из корня проекта):
    uvicorn app.main:app --reload

Документация Swagger:  http://localhost:8000/docs
Документация ReDoc:    http://localhost:8000/redoc
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app import models  # noqa: F401 — импорт нужен, чтобы модели зарегистрировались в Base
from app import auth
from app.routers import patients, departments, doctors, appointments

_STATIC = Path(__file__).parent / "static"

# В режиме разработки создаём таблицы автоматически.
# В продакшене для миграций используйте Alembic (см. README).
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.seed import seed
    seed()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Внутренняя система записи к врачу и управления клиникой",
    version="0.1.0",
    swagger_ui_parameters={"persistAuthorization": True},
    lifespan=lifespan,
)


app.include_router(auth.router,         prefix="/auth",         tags=["Авторизация"])
app.include_router(departments.router,  prefix="/departments",  tags=["Отделения"])
app.include_router(patients.router,    prefix="/patients",    tags=["Пациенты"])
app.include_router(doctors.router,     prefix="/doctors",     tags=["Врачи"])
app.include_router(appointments.router, prefix="/appointments", tags=["Записи на приём"])

app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@app.get("/health", tags=["Система"])
def health_check():
    """Проверка работоспособности сервиса."""
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/", include_in_schema=False)
def read_index():
    return FileResponse(str(_STATIC / "index.html"))


# --------------------------------------------------------------------------- #
#  Роуты Недели 4+ (добавлять по мере реализации):
#
#  from app.routers import doctors, appointments
#  app.include_router(doctors.router,      prefix="/doctors",      tags=["Врачи"])
#  app.include_router(appointments.router, prefix="/appointments", tags=["Записи"])
# --------------------------------------------------------------------------- #
