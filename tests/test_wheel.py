"""
test_wheel.py
Тести для геометрії кільця Колеса Ароматів (14 підгруп).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fragrance_matcher.core.wheel_topology import (
    calculate_ring_distance,
    classify_relationship,
    get_subfamily_relatives,
    SUBFAMILIES_BY_ID,
    TOTAL_SUBFAMILIES
)


def test_circular_distance():
    assert calculate_ring_distance(0, 0) == 0
    assert calculate_ring_distance(0, 1) == 1
    # Перевірка нульового переходу (13 <-> 0)
    assert calculate_ring_distance(13, 0) == 1
    assert calculate_ring_distance(0, 13) == 1
    assert calculate_ring_distance(12, 1) == 3
    # Протилежна точка на колі (діаметр)
    assert calculate_ring_distance(0, 7) == 7
    assert calculate_ring_distance(1, 8) == 7
    print("test_circular_distance: PASSED")


def test_relationships():
    # 0 -> exact
    assert classify_relationship(0) == "exact"
    # 1, 2, 3 -> adjacent
    assert classify_relationship(1) == "adjacent"
    assert classify_relationship(2) == "adjacent"
    assert classify_relationship(3) == "adjacent"
    # 5, 6, 7 -> complementary
    assert classify_relationship(5) == "complementary"
    assert classify_relationship(6) == "complementary"
    assert classify_relationship(7) == "complementary"
    # 4 -> moderate
    assert classify_relationship(4) == "moderate"
    print("test_relationships: PASSED")


def test_subfamily_relatives():
    floral = get_subfamily_relatives("floral_pure")
    assert "floral_pure" in floral["exact"]
    # Сусіди: floral_soft (ring 1) та fresh_aromatic (ring 13)
    assert "floral_soft" in floral["adjacent"]
    assert "fresh_aromatic" in floral["adjacent"]
    # Контраст (протилежний сектор): woody_pure (6) або woody_mossy (7)
    assert "woody_pure" in floral["complementary"] or "woody_mossy" in floral["complementary"]
    print("test_subfamily_relatives: PASSED")


if __name__ == "__main__":
    test_circular_distance()
    test_relationships()
    test_subfamily_relatives()
    print("ALL WHEEL TESTS PASSED!")
