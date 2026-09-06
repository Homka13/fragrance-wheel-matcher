"""
matcher.py
Алгоритмічний рушій метчингу та ранжування ароматів на базі Колеса Едвардса.
Повертає три чіткі категорії рекомендацій:
1. Exact Match (Точний збіг / ідентичний акорд, d = 0)
2. Adjacent Alternatives (Гармонійні суміжні альтернативи, d = 1..2)
3. Complementary Contrasts (Сміливий контраст з протилежного боку, d = 6..7)
"""

from typing import Dict, List, Optional, Set
from .wheel_topology import (
    SUBFAMILIES_BY_ID,
    calculate_ring_distance,
    classify_relationship
)


def compute_pyramid_overlap(
    notes_a: List[str],
    notes_b: List[str]
) -> float:
    """Обчислює коефіцієнт перекриття спільних нот (Жаккар / нормалізоване перетинання)."""
    set_a = {n.lower().strip() for n in notes_a if n}
    set_b = {n.lower().strip() for n in notes_b if n}
    if not set_a or not set_b:
        return 0.0
    intersection = set_a.intersection(set_b)
    union = set_a.union(set_b)
    return len(intersection) / len(union) if union else 0.0


def score_fragrance_match(
    target_fragrance: Dict,
    source_subfamily_id: str,
    source_notes: Optional[List[str]] = None,
    disliked_notes: Optional[List[str]] = None
) -> Optional[Dict]:
    """
    Оцінює кандидатний парфум відносно джерела.
    Повертає словник з оцінкою та категорією або None, якщо аромат відхилений (наприклад, містить небажану ноту).
    """
    target_sf_id = target_fragrance.get("primary_subfamily_id")
    if not target_sf_id or target_sf_id not in SUBFAMILIES_BY_ID:
        return None

    target_notes_all = (
        target_fragrance.get("top_notes", []) +
        target_fragrance.get("heart_notes", []) +
        target_fragrance.get("base_notes", [])
    )
    target_notes_lower = [n.lower().strip() for n in target_notes_all]

    # Перевірка фільтру небажаних нот користувача
    if disliked_notes:
        for bad_note in disliked_notes:
            bn = bad_note.lower().strip()
            if any(bn in tn for tn in target_notes_lower):
                return None  # виключаємо парфум

    src_sf = SUBFAMILIES_BY_ID[source_subfamily_id]
    tgt_sf = SUBFAMILIES_BY_ID[target_sf_id]

    distance = calculate_ring_distance(src_sf["ring_index"], tgt_sf["ring_index"])
    relation = classify_relationship(distance)

    # Розрахунок перекриття нот
    note_similarity = 0.0
    if source_notes:
        note_similarity = compute_pyramid_overlap(source_notes, target_notes_all)

    # Базовий скор топологічної близькості:
    # d = 0 -> 1.0, d = 1 -> 0.85, d = 2 -> 0.71, d = 7 -> 0.0
    topological_score = max(0.0, 1.0 - (distance / 7.0))

    # Загальний скор залежно від типу рекомендації
    if relation == "exact":
        # Для точного збігу пріоритет - перекриття нот і приналежність
        final_score = 0.65 + (0.35 * note_similarity)
    elif relation == "adjacent":
        # Для суміжних: висока вага сусідства (d=1 дає більший скор ніж d=2)
        dist_bonus = 0.20 if distance == 1 else 0.10
        final_score = 0.55 + dist_bonus + (0.25 * note_similarity)
    elif relation == "complementary":
        # Для комплементарних (контраст) оцінюємо чистий контраст протилежного сектору
        contrast_power = 1.0 if distance == 7 else 0.9
        final_score = 0.50 + (0.30 * contrast_power) + (0.20 * (1.0 - note_similarity))
    else:
        final_score = 0.30 + (0.30 * topological_score)

    return {
        "fragrance": target_fragrance,
        "relation": relation,
        "ring_distance": distance,
        "score": round(final_score, 4),
        "target_subfamily": tgt_sf
    }


def find_recommendations(
    all_fragrances: List[Dict],
    source_subfamily_id: Optional[str] = None,
    reference_fragrance_id: Optional[str] = None,
    preferred_notes: Optional[List[str]] = None,
    disliked_notes: Optional[List[str]] = None,
    limit_per_category: int = 6
) -> Dict[str, List[Dict]]:
    """
    Головний інтерфейс метчингу: формує 3 групи рекомендацій
    'exact', 'adjacent', 'complementary'.
    """
    source_notes: List[str] = preferred_notes or []

    # Якщо запит за конкретним парфумом-референсом
    if reference_fragrance_id:
        ref_frag = next((f for f in all_fragrances if f["id"] == reference_fragrance_id), None)
        if ref_frag:
            source_subfamily_id = ref_frag.get("primary_subfamily_id")
            source_notes = (
                ref_frag.get("top_notes", []) +
                ref_frag.get("heart_notes", []) +
                ref_frag.get("base_notes", [])
            )

    if not source_subfamily_id or source_subfamily_id not in SUBFAMILIES_BY_ID:
        raise ValueError(f"Необхідно вказати валідний subfamily_id або reference_fragrance_id: {source_subfamily_id}")

    buckets: Dict[str, List[Dict]] = {
        "exact": [],
        "adjacent": [],
        "complementary": []
    }

    src_sf = SUBFAMILIES_BY_ID[source_subfamily_id]

    for item in all_fragrances:
        # Пропускаємо референсний парфум, якщо підбір іде від нього
        if reference_fragrance_id and item.get("id") == reference_fragrance_id:
            continue

        res = score_fragrance_match(
            target_fragrance=item,
            source_subfamily_id=source_subfamily_id,
            source_notes=source_notes,
            disliked_notes=disliked_notes
        )

        if not res:
            continue

        rel = res["relation"]
        if rel in buckets:
            buckets[rel].append(res)

    # Якщо точних збігів d=0 небагато, додаємо найближчих представників того ж сімейства
    if len(buckets["exact"]) < 2:
        for adj_item in list(buckets["adjacent"]):
            tgt_sf = adj_item.get("target_subfamily", {})
            if tgt_sf.get("family_code") == src_sf.get("family_code") and adj_item["ring_distance"] <= 1:
                promoted = dict(adj_item)
                promoted["relation"] = "exact"
                promoted["score"] = round(adj_item["score"] * 0.95, 4)
                buckets["exact"].append(promoted)

    # Сортуємо кожен кошик за найвищим скором
    for key in buckets:
        buckets[key].sort(key=lambda x: x["score"], reverse=True)
        buckets[key] = buckets[key][:limit_per_category]

    return buckets
