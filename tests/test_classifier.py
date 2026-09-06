"""
test_classifier.py
Тести для класифікатора пірамід нот та українських термінів.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fragrance_matcher.core.pyramid_classifier import (
    map_note_to_subfamily,
    classify_pyramid
)


def test_note_mapping():
    assert map_note_to_subfamily("троянда") == "floral_pure"
    assert map_note_to_subfamily("болгарська троянда") == "floral_pure"
    assert map_note_to_subfamily("бергамот") == "fresh_citrus"
    assert map_note_to_subfamily("морська сіль") == "fresh_aquatic"
    assert map_note_to_subfamily("сандал") == "oriental_woody"
    assert map_note_to_subfamily("ваніль") == "oriental_pure"
    assert map_note_to_subfamily("кедр") == "woody_pure"
    assert map_note_to_subfamily("дубовий мох") == "woody_mossy"
    assert map_note_to_subfamily("шкіра") == "woody_dry"
    print("test_note_mapping: PASSED")


def test_pyramid_classification():
    # Тест композиції типу Lancome La Vie Est Belle (ірис, жасмин, праліне, ваніль, пачулі)
    subfam, fam, scores = classify_pyramid(
        top_notes=["чорна смородина", "груша"],
        heart_notes=["ірис", "жасмин", "флердоранж"],
        base_notes=["праліне", "ваніль", "пачулі", "боби тонка"]
    )
    assert fam in ("oriental", "floral")
    assert subfam in ("oriental_pure", "oriental_woody", "floral_oriental", "floral_pure")

    # Тест чистого цитрусово-акватичного аромату (Armani Acqua di Gio)
    subfam2, fam2, _ = classify_pyramid(
        top_notes=["лайм", "лимон", "бергамот"],
        heart_notes=["морські ноти", "калон"],
        base_notes=["кедр", "мускус"]
    )
    assert fam2 in ("fresh", "woody")
    assert subfam2 in ("fresh_citrus", "fresh_aquatic", "woody_pure")

    print("test_pyramid_classification: PASSED")


if __name__ == "__main__":
    test_note_mapping()
    test_pyramid_classification()
    print("ALL CLASSIFIER TESTS PASSED!")
