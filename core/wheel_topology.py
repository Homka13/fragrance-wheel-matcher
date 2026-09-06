"""
wheel_topology.py
Топологія Колеса Ароматів Майкла Едвардса (14 підгруп у 4 квадрантах).
Реалізує циклічну геометрію кільця та розрахунок відстаней.
"""

from typing import Dict, List, Optional, Tuple

TOTAL_SUBFAMILIES = 14

# 4 Головні Сімейства
FAMILIES: Dict[str, Dict] = {
    "floral": {
        "code": "floral",
        "name_uk": "Квіткові",
        "name_en": "Floral",
        "color_hex": "#E879F9",  # ніжний пурпурово-рожевий
        "profile": "Романтичні, пудрові, елегантні, класичні"
    },
    "oriental": {
        "code": "oriental",
        "name_uk": "Східні (Бурштинові)",
        "name_en": "Oriental / Amber",
        "color_hex": "#F59E0B",  # теплий бурштиновий / золотий
        "profile": "Чуттєві, теплі, насичені, пряні, огортаючі"
    },
    "woody": {
        "code": "woody",
        "name_uk": "Деревні",
        "name_en": "Woody",
        "color_hex": "#10B981",  # глибокий лісовий / смарагдовий
        "profile": "Землянисті, строгі, глибокі, шляхетні, сухі"
    },
    "fresh": {
        "code": "fresh",
        "name_uk": "Свіжі",
        "name_en": "Fresh",
        "color_hex": "#06B6D4",  # яскравий аква / цитрусово-блакитний
        "profile": "Енергійні, чисті, яскраві, бадьорі, іскристі"
    }
}

# 14 Підгруп у порядку розміщення на кільці (0..13)
SUBFAMILIES: List[Dict] = [
    # --- Квіткові (Floral) ---
    {
        "id": "floral_pure",
        "ring_index": 0,
        "family_code": "floral",
        "name_uk": "Квіткові",
        "name_en": "Floral",
        "key_ingredients": ["троянда", "жасмин", "конвалія", "півонія", "гарденія", "тубероза"],
        "profile": "Свіжозрізані квіти, солодкі романтичні пелюстки",
        "color_hex": "#F472B6"
    },
    {
        "id": "floral_soft",
        "ring_index": 1,
        "family_code": "floral",
        "name_uk": "М'які квіткові",
        "name_en": "Soft Floral",
        "key_ingredients": ["ірис", "пудрові ноти", "фіалка", "альдегіди", "мускус"],
        "profile": "Оксамитові, ніжні, пудрові, витончено-ностальгічні",
        "color_hex": "#EC4899"
    },
    {
        "id": "floral_oriental",
        "ring_index": 2,
        "family_code": "floral",
        "name_uk": "Східно-квіткові",
        "name_en": "Floral Oriental",
        "key_ingredients": ["флердоранж", "османтус", "гвоздика", "солодка спеція", "іланг-іланг"],
        "profile": "Теплі квіти з пряним відтінком та пікантним шлейфом",
        "color_hex": "#D946EF"
    },

    # --- Східні (Oriental) ---
    {
        "id": "oriental_soft",
        "ring_index": 3,
        "family_code": "oriental",
        "name_uk": "М'які східні",
        "name_en": "Soft Oriental",
        "key_ingredients": ["ладан", "бензоїн", "м'яка амбра", "кардамон", "мускатний горіх"],
        "profile": "М'які смоли, димні пахощі, приглушена тепла солодкість",
        "color_hex": "#FB923C"
    },
    {
        "id": "oriental_pure",
        "ring_index": 4,
        "family_code": "oriental",
        "name_uk": "Східні",
        "name_en": "Oriental",
        "key_ingredients": ["ваніль", "смоли", "боби тонка", "амбра", "опопонакс"],
        "profile": "Багаті, п'янкі, розкішні, огортаючі східні акорди",
        "color_hex": "#F59E0B"
    },
    {
        "id": "oriental_woody",
        "ring_index": 5,
        "family_code": "oriental",
        "name_uk": "Деревно-східні",
        "name_en": "Woody Oriental",
        "key_ingredients": ["пачулі", "сандал", "темний шоколад", "амброве дерево", "шафран"],
        "profile": "Густі, темні, пряно-деревні з оксамитовою базою",
        "color_hex": "#D97706"
    },

    # --- Деревні (Woody) ---
    {
        "id": "woody_pure",
        "ring_index": 6,
        "family_code": "woody",
        "name_uk": "Деревні",
        "name_en": "Woods",
        "key_ingredients": ["кедр", "ветивер", "дерево уд", "сандалове дерево", "гуаяк"],
        "profile": "Шляхетна суха деревина, тирса, величний лісовий спокій",
        "color_hex": "#059669"
    },
    {
        "id": "woody_mossy",
        "ring_index": 7,
        "family_code": "woody",
        "name_uk": "Мохові деревні (Шипрові)",
        "name_en": "Mossy Woods / Chypre",
        "key_ingredients": ["дубовий мох", "бергамот", "ладанник", "земляні ноти", "листи пачулі"],
        "profile": "Класичний шипровий контраст: вологий мох, лісова прохолода",
        "color_hex": "#10B981"
    },
    {
        "id": "woody_dry",
        "ring_index": 8,
        "family_code": "woody",
        "name_uk": "Сухі деревні (Шкіряні)",
        "name_en": "Dry Woods / Leather",
        "key_ingredients": ["шкіра", "тютюн", "березовий дьоготь", "суха деревина", "дим"],
        "profile": "Димні, строгі, брутальні шкіряні та тютюнові відтінки",
        "color_hex": "#34D399"
    },

    # --- Свіжі (Fresh) ---
    {
        "id": "fresh_citrus",
        "ring_index": 9,
        "family_code": "fresh",
        "name_uk": "Цитрусові",
        "name_en": "Citrus",
        "key_ingredients": ["лимон", "бергамот", "мандарин", "грейпфрут", "лайм", "вербена"],
        "profile": "Іскристі, яскраві, сонячні, соковиті та бадьорі",
        "color_hex": "#06B6D4"
    },
    {
        "id": "fresh_aquatic",
        "ring_index": 10,
        "family_code": "fresh",
        "name_uk": "Водні (Акватичні)",
        "name_en": "Water / Aquatic",
        "key_ingredients": ["морська сіль", "калон", "водорості", "морський бриз", "латаття"],
        "profile": "Прозорі, прохолодні, озонові, наче подих океану",
        "color_hex": "#0EA5E9"
    },
    {
        "id": "fresh_green",
        "ring_index": 11,
        "family_code": "fresh",
        "name_uk": "Зелені",
        "name_en": "Green",
        "key_ingredients": ["скошена трава", "гальбанум", "листя фіалки", "м'ята", "зелений чай"],
        "profile": "Хрусткі, природні, наче зім'яте в руках свіже листя",
        "color_hex": "#38BDF8"
    },
    {
        "id": "fresh_fruity",
        "ring_index": 12,
        "family_code": "fresh",
        "name_uk": "Фруктові",
        "name_en": "Fruity",
        "key_ingredients": ["чорна смородина", "персик", "яблуко", "груша", "малина", "лічі"],
        "profile": "Солодкі, грайливі, десертні свіжі фрукти та ягоди",
        "color_hex": "#818CF8"
    },
    {
        "id": "fresh_aromatic",
        "ring_index": 13,
        "family_code": "fresh",
        "name_uk": "Ароматичні (Фужерні)",
        "name_en": "Aromatic / Fougère",
        "key_ingredients": ["лаванда", "розмарин", "шавлія", "базилік", "чебрець"],
        "profile": "Трав'янисто-пряні, вишукані, сполучна ланка між свіжістю і лісом",
        "color_hex": "#A78BFA"
    }
]

SUBFAMILIES_BY_ID: Dict[str, Dict] = {sf["id"]: sf for sf in SUBFAMILIES}
SUBFAMILIES_BY_INDEX: Dict[int, Dict] = {sf["ring_index"]: sf for sf in SUBFAMILIES}


def calculate_ring_distance(index_a: int, index_b: int) -> int:
    """Обчислює мінімальну циклічну відстань між двома точками на кільці (0..7)."""
    diff = abs(index_a - index_b)
    return min(diff, TOTAL_SUBFAMILIES - diff)


def classify_relationship(distance: int) -> str:
    """
    Класифікує відношення між сегментами:
    - 0: 'exact'
    - 1..3: 'adjacent' (гармонійні сусіди, безпечна альтернатива)
    - 4: 'moderate' (проміжний перехід)
    - 5..7: 'complementary' (діаметрально протилежний контраст)
    """
    if distance == 0:
        return "exact"
    elif distance in (1, 2, 3):
        return "adjacent"
    elif distance in (5, 6, 7):
        return "complementary"
    else:
        return "moderate"


def get_subfamily_relatives(subfamily_id: str) -> Dict[str, List[str]]:
    """Повертає списки підгруп за категоріями зв'язку для заданої підгрупи."""
    if subfamily_id not in SUBFAMILIES_BY_ID:
        raise ValueError(f"Невідома підродина: {subfamily_id}")

    current_idx = SUBFAMILIES_BY_ID[subfamily_id]["ring_index"]
    result = {
        "exact": [subfamily_id],
        "adjacent": [],
        "complementary": [],
        "moderate": []
    }

    for sf in SUBFAMILIES:
        if sf["id"] == subfamily_id:
            continue
        dist = calculate_ring_distance(current_idx, sf["ring_index"])
        rel = classify_relationship(dist)
        result[rel].append(sf["id"])

    return result
