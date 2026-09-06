"""
database.py
Керування підключенням до бази даних (SQLite за замовчуванням або PostgreSQL через DATABASE_URL).
Автоматична ініціалізація та наповнення довідників Колеса Ароматів.
"""

import os
from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base, WheelFamilyModel, WheelSubfamilyModel, BrandModel
from ..core.wheel_topology import FAMILIES, SUBFAMILIES

# Шлях до бази за замовчуванням (локальний файл поруч із проектом)
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "fragrances.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

# Створення engine
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db():
    """Контекстний менеджер для транзакційних сесій БД."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Створює таблиці та наповнює довідники сімейств і підгруп Колеса Едвардса."""
    Base.metadata.create_all(bind=engine)

    with get_db() as session:
        # 1. Заповнюємо 4 сімейства, якщо таблиця порожня
        if session.query(WheelFamilyModel).count() == 0:
            for code, data in FAMILIES.items():
                fam = WheelFamilyModel(
                    code=code,
                    name_uk=data["name_uk"],
                    name_en=data["name_en"],
                    color_hex=data["color_hex"],
                    profile=data["profile"]
                )
                session.add(fam)
            session.flush()

        # 2. Заповнюємо 14 підгруп, якщо порожньо
        if session.query(WheelSubfamilyModel).count() == 0:
            for sf in SUBFAMILIES:
                subfam = WheelSubfamilyModel(
                    id=sf["id"],
                    ring_index=sf["ring_index"],
                    family_code=sf["family_code"],
                    name_uk=sf["name_uk"],
                    name_en=sf["name_en"],
                    color_hex=sf["color_hex"],
                    profile=sf["profile"],
                    key_ingredients=sf["key_ingredients"]
                )
                session.add(subfam)
            session.flush()

    print("База даних успішно ініціалізована та довідники Колеса завантажені.")


if __name__ == "__main__":
    init_db()
