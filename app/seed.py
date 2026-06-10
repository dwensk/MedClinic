"""
Скрипт сидинга (наполнения) базы тестовыми корпоративными данными.

Запуск из корня проекта:
    python -m app.seed

Создаёт: отделения, администратора, врачей (с учётными записями),
графики работы, пациентов и несколько записей на приём.
Скрипт идемпотентен: если данные уже есть, повторно не добавляет.
"""

import random
from datetime import datetime, timedelta, time, timezone

from faker import Faker

from app.auth import _hash_password
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.enums import UserRole, AppointmentStatus
from app.models import (
    User, Department, Doctor, Patient, Schedule, Appointment,
)

fake = Faker(["ru_RU"])
Faker.seed(42)
random.seed(42)


def _random_iin() -> str:
    """Случайный ИИН из 12 цифр (для тестовых данных)."""
    return "".join(random.choices("0123456789", k=12))


def _random_phone() -> str:
    return "+7701" + "".join(random.choices("0123456789", k=7))


# Справочник отделений и типичных специализаций.
DEPARTMENTS = {
    "Терапия": ["Терапевт", "Врач общей практики"],
    "Кардиология": ["Кардиолог"],
    "Неврология": ["Невролог"],
    "Хирургия": ["Хирург", "Травматолог"],
    "Педиатрия": ["Педиатр"],
}


def seed() -> None:
    # Гарантируем, что таблицы существуют.
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(Department).count() > 0:
            print("[!]  Данные уже есть — сидинг пропущен.")
            return

        # 1) Отделения
        departments = {}
        for name in DEPARTMENTS:
            dep = Department(name=name, description=f"Отделение: {name}")
            db.add(dep)
            departments[name] = dep
        db.flush()  # получаем id отделений

        # 2) Администратор
        admin = User(
            email="admin@medklinik.kz",
            hashed_password=_hash_password(settings.ADMIN_PASSWORD),
            full_name="Системный Администратор",
            role=UserRole.admin,
        )
        db.add(admin)

        # 3) Врачи (по 1-2 на отделение) + их графики
        doctors = []
        for dep_name, specs in DEPARTMENTS.items():
            for spec in specs:
                user = User(
                    email=fake.unique.email(),
                    hashed_password=_hash_password(settings.DOCTOR_PASSWORD),
                    full_name=fake.name(),
                    role=UserRole.doctor,
                )
                db.add(user)
                db.flush()

                doctor = Doctor(
                    user_id=user.id,
                    department_id=departments[dep_name].id,
                    iin=_random_iin(),
                    phone=_random_phone(),
                    specialization=spec,
                    cabinet=str(random.randint(101, 320)),
                )
                db.add(doctor)
                db.flush()
                doctors.append(doctor)

                # График: Пн-Пт, 09:00-17:00
                for weekday in range(0, 5):
                    db.add(Schedule(
                        doctor_id=doctor.id,
                        weekday=weekday,
                        start_time=time(9, 0),
                        end_time=time(17, 0),
                    ))

        # 4) Пациенты
        patients = []
        for _ in range(15):
            patient = Patient(
                full_name=fake.name(),
                iin=_random_iin(),
                phone=_random_phone(),
                birth_date=fake.date_of_birth(minimum_age=1, maximum_age=90),
                gender=random.choice(["М", "Ж"]),
            )
            db.add(patient)
            patients.append(patient)
        db.flush()

        # 5) Записи на приём (в будущем — чтобы проходили валидацию)
        for _ in range(20):
            doctor = random.choice(doctors)
            patient = random.choice(patients)
            future = datetime.now(timezone.utc) + timedelta(
                days=random.randint(1, 14),
                hours=random.randint(9, 16),
            )
            db.add(Appointment(
                doctor_id=doctor.id,
                patient_id=patient.id,
                scheduled_at=future.replace(minute=0, second=0, microsecond=0),
                status=AppointmentStatus.scheduled,
                reason=random.choice(["Консультация", "Профосмотр", "Жалобы", "Повторный приём"]),
            ))

        db.commit()
        print("[OK] Сидинг завершён:")
        print(f"   Отделений: {db.query(Department).count()}")
        print(f"   Пользователей: {db.query(User).count()}")
        print(f"   Врачей: {db.query(Doctor).count()}")
        print(f"   Пациентов: {db.query(Patient).count()}")
        print(f"   Записей на приём: {db.query(Appointment).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
