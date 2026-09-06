"""
ingest.py
Конвеєр обробки та завантаження парфумерних релізів.
Реалізує Data Quality Gate: відхиляє записи без валідного мапінгу на Колесо Ароматів
та виконує ідемпотентний upsert у базу даних.
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

from pydantic import ValidationError
from sqlalchemy.orm import Session

from .schemas import RawFragranceInput, ValidatedFragrance
from ..core.pyramid_classifier import classify_pyramid
from ..core.wheel_topology import SUBFAMILIES_BY_ID
from ..db.database import get_db, init_db
from ..db.models import BrandModel, FragranceModel, RecommendationCacheModel
from ..core.wheel_topology import calculate_ring_distance, classify_relationship

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_pipeline")


def slugify_brand(name: str) -> str:
    """Генерує безпечний slug для бренду."""
    clean = re.sub(r"[^\w\s-]", "", name.lower()).strip()
    return re.sub(r"[\s_-]+", "_", clean)


def process_and_ingest_records(raw_items: List[Dict]) -> Dict:
    """
    Головна функція конвеєра:
    1. Валідація Pydantic
    2. Data Quality Gate (перевірка прив'язки до Колеса)
    3. Ідемпотентний Upsert у БД
    4. Оновлення кешу суміжностей
    """
    init_db()

    total = len(raw_items)
    upserted_count = 0
    skipped_records = []
    validated_list: List[ValidatedFragrance] = []

    # 1. Валідація та Data Quality Gate
    for item in raw_items:
        try:
            raw = RawFragranceInput(**item)
        except ValidationError as e:
            skipped_records.append({
                "item": item.get("name", "Unknown"),
                "reason": f"Pydantic validation error: {str(e)}"
            })
            continue

        # Класифікація піраміди
        primary_subfam, family_code, profile_scores = classify_pyramid(
            top_notes=raw.top_notes,
            heart_notes=raw.heart_notes,
            base_notes=raw.base_notes,
            declared_family_hint=raw.declared_family
        )

        # DATA QUALITY GATE: жорстке правило блокування
        if not primary_subfam or primary_subfam not in SUBFAMILIES_BY_ID:
            logger.warning(f"Data Quality Gate відхилив запис: '{raw.name}' (бренд: {raw.brand_name}) - не вдалося визначити групу Колеса!")
            skipped_records.append({
                "item": raw.name,
                "brand": raw.brand_name,
                "reason": "Data Quality Gate: відсутня обов'язкова прив'язка до 14 підгруп Колеса"
            })
            continue

        brand_id = raw.brand_id or slugify_brand(raw.brand_name)

        val = ValidatedFragrance(
            id=raw.id,
            brand_id=brand_id,
            brand_name=raw.brand_name,
            name=raw.name,
            gender=raw.gender or "unisex",
            concentration=raw.concentration or "EDP",
            primary_subfamily_id=primary_subfam,
            family_code=family_code,
            top_notes=raw.top_notes,
            heart_notes=raw.heart_notes,
            base_notes=raw.base_notes,
            price_uah=raw.price_uah,
            brocard_sku=raw.brocard_sku,
            brocard_url=raw.brocard_url,
            image_url=raw.image_url
        )
        validated_list.append(val)

    # 2. Збереження у БД (ідемпотентний Upsert)
    with get_db() as session:
        for val in validated_list:
            # Перевірка/створення бренду
            brand = session.query(BrandModel).filter_by(id=val.brand_id).first()
            if not brand:
                brand = BrandModel(id=val.brand_id, name=val.brand_name)
                session.add(brand)
                session.flush()

            # Перевірка/оновлення парфуму
            fragrance = session.query(FragranceModel).filter_by(id=val.id).first()
            if fragrance:
                fragrance.name = val.name
                fragrance.brand_id = val.brand_id
                fragrance.gender = val.gender
                fragrance.concentration = val.concentration
                fragrance.primary_subfamily_id = val.primary_subfamily_id
                fragrance.top_notes = val.top_notes
                fragrance.heart_notes = val.heart_notes
                fragrance.base_notes = val.base_notes
                fragrance.price_uah = val.price_uah
                fragrance.brocard_sku = val.brocard_sku
                fragrance.brocard_url = val.brocard_url
                fragrance.image_url = val.image_url
            else:
                fragrance = FragranceModel(
                    id=val.id,
                    brand_id=val.brand_id,
                    name=val.name,
                    gender=val.gender,
                    concentration=val.concentration,
                    primary_subfamily_id=val.primary_subfamily_id,
                    top_notes=val.top_notes,
                    heart_notes=val.heart_notes,
                    base_notes=val.base_notes,
                    price_uah=val.price_uah,
                    brocard_sku=val.brocard_sku,
                    brocard_url=val.brocard_url,
                    image_url=val.image_url
                )
                session.add(fragrance)

            upserted_count += 1

        session.flush()

        # 3. Оновлення кешу рекомендацій для завантажених парфумів
        all_frags = session.query(FragranceModel).all()
        for f1 in all_frags:
            sf1 = SUBFAMILIES_BY_ID.get(f1.primary_subfamily_id)
            if not sf1:
                continue
            for f2 in all_frags:
                if f1.id == f2.id:
                    continue
                sf2 = SUBFAMILIES_BY_ID.get(f2.primary_subfamily_id)
                if not sf2:
                    continue

                dist = calculate_ring_distance(sf1["ring_index"], sf2["ring_index"])
                match_type = classify_relationship(dist)
                score = round(max(0.1, 1.0 - (dist / 7.0)), 4)

                cached = session.query(RecommendationCacheModel).filter_by(
                    source_fragrance_id=f1.id,
                    target_fragrance_id=f2.id
                ).first()

                if cached:
                    cached.match_type = match_type
                    cached.ring_distance = dist
                    cached.similarity_score = score
                else:
                    new_cache = RecommendationCacheModel(
                        source_fragrance_id=f1.id,
                        target_fragrance_id=f2.id,
                        match_type=match_type,
                        ring_distance=dist,
                        similarity_score=score
                    )
                    session.add(new_cache)

    logger.info(f"Пайплайн завершено: всього {total}, збережено {upserted_count}, відхилено Data Quality Gate {len(skipped_records)}")
    return {
        "total_processed": total,
        "upserted": upserted_count,
        "skipped_count": len(skipped_records),
        "skipped_details": skipped_records
    }


def ingest_from_file(json_file_path: str) -> Dict:
    """Завантажує JSON-файл та пропускає через конвеєр."""
    path = Path(json_file_path)
    if not path.exists():
        raise FileNotFoundError(f"Файл не знайдено: {json_file_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("products", data if isinstance(data, list) else [])
    return process_and_ingest_records(items)
