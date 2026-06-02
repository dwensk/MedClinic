from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, SessionLocal
from app import models
from app.auth import hash_password
from app.routers import auth, users, doctors, schedules, appointments, medical_records


def seed_data():
    """Тестілік деректер — бірінші іске қосқанда толтырылады"""
    db = SessionLocal()
    try:
        if db.query(models.User).first():
            return  # Деректер бар болса, өткізіп кету

        # Admin жасау
        admin = models.User(
            name="Главный Администратор",
            email="admin@medclinic.kz",
            password_hash=hash_password("admin123"),
            role=models.RoleEnum.admin,
            phone="+7 701 000 0001"
        )
        db.add(admin)

        # Дәрігер пайдаланушылары
        doc_user1 = models.User(
            name="Айгүл Сейткалиева",
            email="doctor1@medclinic.kz",
            password_hash=hash_password("doctor123"),
            role=models.RoleEnum.doctor,
            phone="+7 701 000 0002"
        )
        doc_user2 = models.User(
            name="Бауыржан Мұқанов",
            email="doctor2@medclinic.kz",
            password_hash=hash_password("doctor123"),
            role=models.RoleEnum.doctor,
            phone="+7 701 000 0003"
        )

        # Пациент пайдаланушылары
        patient1 = models.User(
            name="Замира Нұрланова",
            email="patient1@medclinic.kz",
            password_hash=hash_password("patient123"),
            role=models.RoleEnum.patient,
            phone="+7 705 111 2233"
        )
        patient2 = models.User(
            name="Дәурен Сейітқалиев",
            email="patient2@medclinic.kz",
            password_hash=hash_password("patient123"),
            role=models.RoleEnum.patient,
            phone="+7 707 222 3344"
        )

        db.add_all([doc_user1, doc_user2, patient1, patient2])
        db.commit()

        # Дәрігер профильдары
        doctor1 = models.Doctor(
            user_id=doc_user1.id,
            specialty="Терапевт",
            cabinet="101",
            experience_years=8,
            bio="Жалпы терапия, профилактикалық тексеру"
        )
        doctor2 = models.Doctor(
            user_id=doc_user2.id,
            specialty="Кардиолог",
            cabinet="205",
            experience_years=12,
            bio="Жүрек ауруларының алдын алу мен емдеу"
        )
        db.add_all([doctor1, doctor2])
        db.commit()

        # Жұмыс кестелері
        schedules_data = [
            models.Schedule(doctor_id=doctor1.id, day_of_week="monday",
                            start_time="09:00", end_time="17:00", slot_duration_min=30),
            models.Schedule(doctor_id=doctor1.id, day_of_week="wednesday",
                            start_time="09:00", end_time="17:00", slot_duration_min=30),
            models.Schedule(doctor_id=doctor1.id, day_of_week="friday",
                            start_time="09:00", end_time="13:00", slot_duration_min=30),
            models.Schedule(doctor_id=doctor2.id, day_of_week="tuesday",
                            start_time="10:00", end_time="18:00", slot_duration_min=45),
            models.Schedule(doctor_id=doctor2.id, day_of_week="thursday",
                            start_time="10:00", end_time="18:00", slot_duration_min=45),
        ]
        db.add_all(schedules_data)
        db.commit()

        print("✅ Тестілік деректер сәтті жүктелді")
        print("   Admin:   admin@medclinic.kz / admin123")
        print("   Дәрігер: doctor1@medclinic.kz / doctor123")
        print("   Пациент: patient1@medclinic.kz / patient123")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed қате: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    seed_data()
    yield


app = FastAPI(
    title="МедКлиник — Дәрігерге жазылу жүйесі",
    description="Корпоративтік медициналық жүйе: жазылу, кесте, медициналық карта",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(doctors.router)
app.include_router(schedules.router)
app.include_router(appointments.router)
app.include_router(medical_records.router)


@app.get("/", tags=["Басты бет"])
def root():
    return {
        "жүйе": "МедКлиник",
        "нұсқа": "1.0.0",
        "swagger": "/docs",
        "redoc": "/redoc",
        "күй": "жұмыс істеп тұр ✅"
    }
