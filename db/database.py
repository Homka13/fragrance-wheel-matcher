"""
database.py
Керування підключенням до бази даних (SQLite за замовчуванням або PostgreSQL через DATABASE_URL).
Автоматична ініціалізація та наповнення довідників Колеса Ароматів.
"""

import os
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

try:
    from db.models import Base, WheelFamilyModel, WheelSubfamilyModel, BrandModel
except ImportError:
    from .models import Base, WheelFamilyModel, WheelSubfamilyModel, BrandModel

try:
    from core.wheel_topology import FAMILIES, SUBFAMILIES
except ImportError:
    try:
        from ..core.wheel_topology import FAMILIES, SUBFAMILIES
    except ImportError:
        from fragrance_matcher.core.wheel_topology import FAMILIES, SUBFAMILIES

# Шлях до бази за замовчуванням (DuckDB для аналітики та швидких ймовірнісних розрахунків)
DEFAULT_DB_FILE = os.getenv("DB_FILENAME", "fragrances.duckdb")
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / DEFAULT_DB_FILE

# На Vercel / AWS Lambda коренева папка read-only, тому використовуємо /tmp якщо немає прав запису
try:
    test_file = DEFAULT_DB_PATH.parent / ".write_test"
    test_file.touch()
    test_file.unlink()
except (PermissionError, OSError):
    DEFAULT_DB_PATH = Path("/tmp") / DEFAULT_DB_FILE

DEFAULT_DIALECT = "duckdb" if str(DEFAULT_DB_PATH).endswith(".duckdb") else "sqlite"
DATABASE_URL = os.getenv("DATABASE_URL", f"{DEFAULT_DIALECT}:///{DEFAULT_DB_PATH}")

# Створення engine
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_duckdb_con(read_only: bool = False):
    """
    Повертає пряме з'єднання з DuckDB для аналітичних розрахунків,
    матриць ймовірностей, векторних відстаней та швидких агрегацій.
    """
    import duckdb
    duck_path = DEFAULT_DB_PATH if str(DEFAULT_DB_PATH).endswith(".duckdb") else DEFAULT_DB_PATH.with_suffix(".duckdb")
    return duckdb.connect(str(duck_path), read_only=read_only)


def sync_to_sqlite(sqlite_path: Optional[Path] = None):
    """
    Синхронізує та експортує дані з DuckDB у файл SQLite (fragrances.db),
    щоб їх можна було відкривати у графічних програмах, таких як 'DB Browser for SQLite'.
    """
    target_sqlite = sqlite_path or (DEFAULT_DB_PATH.parent / "fragrances.db")
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("INSTALL sqlite; LOAD sqlite;")
            conn.exec_driver_sql(f"ATTACH '{target_sqlite}' AS sqlite_db (TYPE SQLITE);")
            for tbl in ["wheel_families", "wheel_subfamilies", "brands", "fragrances"]:
                try:
                    conn.exec_driver_sql(f"CREATE OR REPLACE TABLE sqlite_db.{tbl} AS SELECT * FROM {tbl};")
                except Exception as te:
                    print(f"Таблиця {tbl} пропущена при синхронізації: {te}")
            conn.commit()
            conn.exec_driver_sql("DETACH sqlite_db;")
        print(f"Дані успішно експортовано в SQLite: {target_sqlite}")
    except Exception as e:
        print(f"Помилка експорту в SQLite: {e}")


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
