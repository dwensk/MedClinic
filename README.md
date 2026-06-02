# 🏥 МедКлиник — Дәрігерге жазылу жүйесі

Корпоративтік медициналық веб-жүйе. FastAPI + SQLAlchemy + SQLite/PostgreSQL.

## Технологиялар

| Құрал | Мақсаты |
|-------|---------|
| FastAPI | REST API фреймворк |
| SQLAlchemy | ORM (дерекқормен жұмыс) |
| SQLite / PostgreSQL | Дерекқор |
| Passlib + bcrypt | Құпия сөзді хэштеу |
| python-jose | JWT токендер |
| Pydantic | Деректерді валидациялау |
| Uvicorn | ASGI веб-сервер |

## Жоба құрылымы

```
medclinic/
├── app/
│   ├── main.py          # FastAPI қосымшасы, lifespan, CORS
│   ├── database.py      # SQLAlchemy қосылымы
│   ├── models.py        # ORM кестелер (User, Doctor, Schedule, Appointment, MedicalRecord)
│   ├── schemas.py       # Pydantic схемалары + валидация
│   ├── auth.py          # JWT + bcrypt утилиталары
│   ├── dependencies.py  # Рөлге негізделген рұқсат (RBAC)
│   └── routers/
│       ├── auth.py           # POST /auth/register, POST /auth/login
│       ├── users.py          # GET/PATCH /users/me, Admin: GET/DELETE /users/{id}
│       ├── doctors.py        # CRUD /doctors
│       ├── schedules.py      # CRUD /schedules
│       ├── appointments.py   # CRUD /appointments
│       └── medical_records.py# CRUD /records
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Дерекқор схемасы (ERD)

```
users ─────────────┬──── appointments (patient_id)
  │                └──── medical_records (patient_id)
  └── doctors ──────┬──── schedules
                    ├──── appointments (doctor_id)
                    └──── medical_records (doctor_id)
                              │
                    appointments ── medical_records (appointment_id)
```

## Рөлдер және рұқсаттар

| Әрекет | Пациент | Дәрігер | Әкімші |
|--------|---------|---------|--------|
| Тіркелу / Кіру | ✅ | ✅ | ✅ |
| Дәрігерлерді көру | ✅ | ✅ | ✅ |
| Жазылу жасау | ✅ | ❌ | ✅ |
| Өз жазылуларын көру | ✅ | ✅ | ✅ |
| Жазылу күйін өзгерту | болдырмау | бекіту/болды | ✅ |
| Медициналық карта жасау | ❌ | ✅ | ✅ |
| Пайдаланушы рөлін өзгерту | ❌ | ❌ | ✅ |
| Дәрігер профилін жасау | ❌ | ❌ | ✅ |

## Іске қосу

### 1. Репозиторийді клондау
```bash
git clone https://github.com/sizdin-username/medclinic.git
cd medclinic
```

### 2. Виртуал орта жасау
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Тәуелділіктерді орнату
```bash
pip install -r requirements.txt
```

### 4. Орта айнымалыларын баптау
```bash
cp .env.example .env
# .env файлын өңдеп, SECRET_KEY өзгертіңіз
```

### 5. Серверді іске қосу
```bash
uvicorn app.main:app --reload
```

API мекенжайы: http://localhost:8000  
Swagger UI: http://localhost:8000/docs

## Тестілік аккаунттар (автоматты жүктеледі)

| Рөл | Email | Құпия сөз |
|-----|-------|-----------|
| Admin | admin@medclinic.kz | admin123 |
| Дәрігер | doctor1@medclinic.kz | doctor123 |
| Пациент | patient1@medclinic.kz | patient123 |

## Негізгі API эндпоинттері

### Аутентификация
```
POST /auth/register    — Тіркелу
POST /auth/login       — Кіру (JWT токен алу)
```

### Дәрігерлер
```
GET    /doctors              — Барлық дәрігерлер (фильтр: ?specialty=Терапевт)
GET    /doctors/{id}         — Дәрігер профилі
POST   /doctors              — Дәрігер жасау [Admin]
PATCH  /doctors/{id}         — Профиль жаңарту [Doctor/Admin]
DELETE /doctors/{id}         — Өшіру [Admin]
```

### Жазылу
```
POST   /appointments                    — Жазылу жасау [Patient]
GET    /appointments/my                 — Өз жазылуларым
GET    /appointments/doctor/{id}        — Дәрігердің жазылулары [Doctor/Admin]
PATCH  /appointments/{id}/status        — Күй өзгерту
```

### Медициналық карта
```
POST   /records                     — Жазба жасау [Doctor]
GET    /records/patient/{id}        — Пациент картасы
PATCH  /records/{id}               — Жаңарту [Doctor]
```

## Деплой (Render)

1. GitHub-қа push жасаңыз
2. [render.com](https://render.com) сайтына кіріңіз
3. "New Web Service" → GitHub репоны байланыстырыңыз
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Environment Variables: `.env` файлындағы мәндерді қосыңыз

## Авторлар

- [Аты-жөніңіз] — Backend (FastAPI, дерекқор, аутентификация)
- [Командалас 2] — ...
- [Командалас 3] — ...
