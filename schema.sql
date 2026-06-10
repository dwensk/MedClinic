-- ============================================================
--  МедКлиник — схема БД (PostgreSQL)
--  7 связанных нормализованных таблиц.
--  Этот файл — справочная DDL-документация. В приложении таблицы
--  создаются через SQLAlchemy / Alembic, но схема полностью идентична.
-- ============================================================

CREATE TYPE user_role AS ENUM ('admin', 'doctor');
CREATE TYPE appointment_status AS ENUM ('scheduled', 'completed', 'cancelled', 'no_show');

-- Учётные записи (вход в систему): администраторы и врачи
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(150) NOT NULL,
    role            user_role    NOT NULL DEFAULT 'doctor',
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Отделения клиники (справочник)
CREATE TABLE departments (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(120) NOT NULL UNIQUE,
    description TEXT
);

-- Профиль врача (1:1 к users, N:1 к departments)
CREATE TABLE doctors (
    id             SERIAL PRIMARY KEY,
    user_id        INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    department_id  INTEGER NOT NULL REFERENCES departments(id),
    iin            VARCHAR(12) NOT NULL UNIQUE,
    phone          VARCHAR(20) NOT NULL,
    specialization VARCHAR(120) NOT NULL,
    cabinet        VARCHAR(20)
);

-- Пациенты
CREATE TABLE patients (
    id         SERIAL PRIMARY KEY,
    full_name  VARCHAR(150) NOT NULL,
    iin        VARCHAR(12)  NOT NULL UNIQUE,
    phone      VARCHAR(20)  NOT NULL,
    birth_date DATE,
    gender     VARCHAR(10),
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- График работы врачей
CREATE TABLE schedules (
    id         SERIAL PRIMARY KEY,
    doctor_id  INTEGER NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    weekday    INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),  -- 0=Пн ... 6=Вс
    start_time TIME    NOT NULL,
    end_time   TIME    NOT NULL,
    CONSTRAINT uq_doctor_weekday UNIQUE (doctor_id, weekday)
);

-- Записи на приём
CREATE TABLE appointments (
    id           SERIAL PRIMARY KEY,
    doctor_id    INTEGER NOT NULL REFERENCES doctors(id),
    patient_id   INTEGER NOT NULL REFERENCES patients(id),
    scheduled_at TIMESTAMPTZ NOT NULL,
    status       appointment_status NOT NULL DEFAULT 'scheduled',
    reason       VARCHAR(255),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Медицинские записи (результат приёма, 1:1 к appointments)
CREATE TABLE medical_records (
    id             SERIAL PRIMARY KEY,
    appointment_id INTEGER NOT NULL UNIQUE REFERENCES appointments(id) ON DELETE CASCADE,
    diagnosis      TEXT NOT NULL,
    prescription   TEXT,
    notes          TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Индексы для частых поисков
CREATE INDEX idx_appointments_doctor  ON appointments(doctor_id);
CREATE INDEX idx_appointments_patient ON appointments(patient_id);
CREATE INDEX idx_appointments_time    ON appointments(scheduled_at);
