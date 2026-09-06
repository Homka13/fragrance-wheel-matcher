"""
test_pipeline.py
Тести для Data Quality Gate, валідації Pydantic та рушія метчингу.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fragrance_matcher.pipeline.ingest import process_and_ingest_records
from fragrance_matcher.core.matcher import find_recommendations
from fragrance_matcher.db.database import get_db
from fragrance_matcher.db.models import FragranceModel


def test_data_quality_gate():
    # 1 валідний запис + 1 невалідний (без нот та без групи)
    test_batch = [
        {
            "id": "valid_rose_perfume",
            "name": "Pure Rose Elixir",
            "brand_name": "Lancôme",
            "top_notes": ["рожевий перець"],
            "heart_notes": ["троянда", "півонія"],
            "base_notes": ["мускус", "кедр"]
        },
        {
            "id": "invalid_junk_item",
            "name": "Unknown Mystery Water",
            "brand_name": "FakeBrand",
            # Повністю порожні або невідомі ноти
            "top_notes": ["абвгде", "12345"],
            "heart_notes": [],
            "base_notes": []
        }
    ]

    res = process_and_ingest_records(test_batch)

    # Перевіряємо, що 1 прийнято, 1 заблоковано Data Quality Gate
    assert res["upserted"] >= 1
    assert res["skipped_count"] == 1
    assert "відсутня обов'язкова прив'язка" in res["skipped_details"][0]["reason"]
    print("test_data_quality_gate: PASSED")


def test_matcher_buckets():
    with get_db() as session:
        frags = session.query(FragranceModel).all()
        all_frags = [f.to_dict() for f in frags]

    assert len(all_frags) > 0

    # Шукаємо рекомендації для квіткового сегменту
    recs = find_recommendations(
        all_fragrances=all_frags,
        source_subfamily_id="floral_pure",
        limit_per_category=5
    )

    assert "exact" in recs
    assert "adjacent" in recs
    assert "complementary" in recs

    # Перевіряємо скори
    for item in recs["exact"]:
        assert item["relation"] == "exact"
        assert item["ring_distance"] == 0

    for item in recs["adjacent"]:
        assert item["relation"] == "adjacent"
        assert item["ring_distance"] in (1, 2)

    for item in recs["complementary"]:
        assert item["relation"] == "complementary"
        assert item["ring_distance"] in (6, 7)

    print("test_matcher_buckets: PASSED")


if __name__ == "__main__":
    test_data_quality_gate()
    test_matcher_buckets()
    print("ALL PIPELINE & MATCHER TESTS PASSED!")
