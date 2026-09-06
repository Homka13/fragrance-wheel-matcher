"""
run.py
Єдина точка запуску сервісу Fragrance Wheel Matcher:
1. Ініціалізує локальну базу даних SQLite.
2. Проганяє Data Quality Gate та завантажує стартовий каталог бестселерів Brocard.
3. Запускає веб-сервер на http://localhost:8000.
"""

import os
import sys
from pathlib import Path

# Додаємо кореневу папку до PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT.parent))

from fragrance_matcher.db.database import init_db, get_db
from fragrance_matcher.db.models import FragranceModel
from fragrance_matcher.pipeline.ingest import ingest_from_file

def main():
    print("=" * 60)
    print("  🌸 FRAGRANCE WHEEL MATCHER (Колесо Ароматів Brocard) 🌸")
    print("=" * 60)

    # 1. Ініціалізація БД
    print("\n[1/3] Перевірка та ініціалізація бази даних SQLite...")
    init_db()

    # 2. Перевірка наявності даних
    with get_db() as session:
        count = session.query(FragranceModel).count()
        print(f"Поточна кількість парфумів у базі: {count}")

        if count == 0:
            seed_file = PROJECT_ROOT / "data" / "seed_brocard_catalog.json"
            if seed_file.exists():
                print(f"\n[2/3] Запуск Data Quality Gate та імпорт каталогу з {seed_file.name}...")
                res = ingest_from_file(str(seed_file))
                print(f"-> Оброблено: {res['total_processed']}, збережено: {res['upserted']}, відхилено: {res['skipped_count']}")
            else:
                print("\n[2/3] Seed-файл не знайдено, пропускаємо імпорт.")
        else:
            print("\n[2/3] Каталог уже завантажений у БД.")

    # 3. Запуск веб-сервера
    print("\n[3/3] Запуск локального веб-сервера...")
    print("\n" + " ✨ " * 15)
    print("  🚀 Додаток готовий до роботи!")
    print("  👉 Відкрийте у браузері: http://localhost:8000")
    print(" ✨ " * 15 + "\n")

    import uvicorn
    uvicorn.run("fragrance_matcher.app.main:app", host="127.0.0.1", port=8000, reload=False, log_level="info")

if __name__ == "__main__":
    main()
