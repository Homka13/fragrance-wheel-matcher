#!/usr/bin/env python3
"""
run_scraper.py
CLI скрипт для запуску парсингу каталогу Brocard та завантаження в DuckDB / SQLite.
"""

import argparse
import asyncio
import json
import logging
import os
import sys

from scrapers.brocard_scraper import run_scraper_cli

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_scraper")


def parse_args():
    parser = argparse.ArgumentParser(description="Скрапер парфумерії Brocard.ua (чоловічі, жіночі, унісекс)")
    parser.add_argument("--female", type=int, default=50, help="Кількість жіночих ароматів (за замовчуванням: 50)")
    parser.add_argument("--male", type=int, default=50, help="Кількість чоловічих ароматів (за замовчуванням: 50)")
    parser.add_argument("--unisex", type=int, default=50, help="Кількість унісекс / нішевих ароматів (за замовчуванням: 50)")
    parser.add_argument("--output", type=str, default="data/brocard_scraped_150.json", help="Шлях до файлу збереження JSON")
    parser.add_argument("--headless", action="store_true", help="Запуск браузера у фоновому режимі без UI вікна")
    parser.add_argument("--skip-db", action="store_true", help="Пропустити автоматичний імпорт у базу даних")
    return parser.parse_args()


async def main():
    args = parse_args()

    targets = {}
    if args.female > 0:
        targets["female"] = args.female
    if args.male > 0:
        targets["male"] = args.male
    if args.unisex > 0:
        targets["unisex"] = args.unisex

    if not targets:
        logger.error("Не вибрано жодної категорії для збору! Вкажіть хоча б одну з: --female, --male, --unisex")
        sys.exit(1)

    total_target = sum(targets.values())
    logger.info(f"Запуск скрапера Brocard. Ціль: {total_target} ароматів {targets}")

    products = await run_scraper_cli(
        targets=targets,
        output_file=args.output,
        headless=args.headless,
        skip_db=args.skip_db
    )
    logger.info(f"Процес завершено успішно! Оброблено {len(products)} парфумів.")


if __name__ == "__main__":
    asyncio.run(main())
