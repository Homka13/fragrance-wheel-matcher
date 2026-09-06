"""
pyramid_classifier.py
Класифікатор ольфакторних пірамід та нормалізатор парфумерних нот.
Здійснює мапінг сирих назв нот (українською та англійською) на 14 підгруп Колеса Едвардса.
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from .wheel_topology import SUBFAMILIES, SUBFAMILIES_BY_ID, FAMILIES

# Словник синонімів та інгредієнтів для кожної підгрупи
# Включає українські та англійські форми в називному/родовому відмінках
NOTE_KEYWORD_MAP: Dict[str, str] = {
    # --- Floral (floral_pure) ---
    "троянда": "floral_pure", "троянди": "floral_pure", "rose": "floral_pure", "damask rose": "floral_pure",
    "жасмин": "floral_pure", "жасмину": "floral_pure", "jasmine": "floral_pure",
    "конвалія": "floral_pure", "конвалії": "floral_pure", "lily of the valley": "floral_pure",
    "півонія": "floral_pure", "півонії": "floral_pure", "peony": "floral_pure",
    "гарденія": "floral_pure", "gardenia": "floral_pure",
    "тубероза": "floral_pure", "туберози": "floral_pure", "tuberose": "floral_pure",
    "магнолія": "floral_pure", "magnolia": "floral_pure",
    "бузок": "floral_pure", "lilac": "floral_pure",
    "лілія": "floral_pure", "лілії": "floral_pure", "lily": "floral_pure",
    "квіткові ноти": "floral_pure", "квітковий акорд": "floral_pure", "floral notes": "floral_pure",

    # --- Soft Floral (floral_soft) ---
    "ірис": "floral_soft", "ірису": "floral_soft", "iris": "floral_soft", "orris": "floral_soft",
    "фіалка": "floral_soft", "фіалки": "floral_soft", "violet": "floral_soft",
    "пудрові ноти": "floral_soft", "пудра": "floral_soft", "powdery notes": "floral_soft",
    "альдегіди": "floral_soft", "альдегідні ноти": "floral_soft", "aldehydes": "floral_soft",
    "геліотроп": "floral_soft", "heliotrope": "floral_soft",

    # --- Floral Oriental (floral_oriental) ---
    "флердоранж": "floral_oriental", "цвіт апельсина": "floral_oriental", "orange blossom": "floral_oriental", "neroli": "floral_oriental", "неролі": "floral_oriental",
    "іланг-іланг": "floral_oriental", "іланг": "floral_oriental", "ylang-ylang": "floral_oriental",
    "османтус": "floral_oriental", "osmanthus": "floral_oriental",
    "гвоздика (квітка)": "floral_oriental", "carnation": "floral_oriental",
    "тіаре": "floral_oriental", "tiare": "floral_oriental",

    # --- Soft Oriental (oriental_soft) ---
    "ладан": "oriental_soft", "incense": "floral_oriental", "olibanum": "oriental_soft",
    "бензоїн": "oriental_soft", "benzoin": "oriental_soft",
    "м'яка амбра": "oriental_soft", "soft amber": "oriental_soft",
    "кардамон": "oriental_soft", "cardamom": "oriental_soft",
    "мускатний горіх": "oriental_soft", "nutmeg": "oriental_soft",
    "кориця": "oriental_soft", "cinnamon": "oriental_soft",
    "мирра": "oriental_soft", "myrrh": "oriental_soft",

    # --- Oriental (oriental_pure) ---
    "ваніль": "oriental_pure", "ванілі": "oriental_pure", "vanilla": "oriental_pure",
    "амбра": "oriental_pure", "амбри": "oriental_pure", "amber": "oriental_pure",
    "боби тонка": "oriental_pure", "бобів тонка": "oriental_pure", "tonka bean": "oriental_pure",
    "мускус": "oriental_pure", "мускусу": "oriental_pure", "musk": "oriental_pure", "white musk": "oriental_pure", "білий мускус": "oriental_pure",
    "опопонакс": "oriental_pure", "opoponax": "oriental_pure",
    "східні ноти": "oriental_pure", "смоли": "oriental_pure", "resins": "oriental_pure",
    "карамель": "oriental_pure", "caramel": "oriental_pure",
    "праліне": "oriental_pure", "praline": "oriental_pure",

    # --- Woody Oriental (oriental_woody) ---
    "пачулі": "oriental_woody", "patchouli": "oriental_woody",
    "сандал": "oriental_woody", "сандалове дерево": "oriental_woody", "sandalwood": "oriental_woody",
    "темний шоколад": "oriental_woody", "chocolate": "oriental_woody", "какао": "oriental_woody", "cacao": "oriental_woody",
    "шафран": "oriental_woody", "saffron": "oriental_woody",
    "амброве дерево": "oriental_woody", "amberwood": "oriental_woody", "ambroxan": "oriental_woody", "амброксан": "oriental_woody",

    # --- Woods (woody_pure) ---
    "кедр": "woody_pure", "кедра": "woody_pure", "cedar": "woody_pure", "cedarwood": "woody_pure",
    "ветивер": "woody_pure", "ветиверу": "woody_pure", "vetiver": "woody_pure",
    "уд": "woody_pure", "дерево уд": "woody_pure", "agarwood": "woody_pure", "oud": "woody_pure",
    "гуаяк": "woody_pure", "дерево гуаяк": "woody_pure", "guaiac wood": "woody_pure",
    "кипарис": "woody_pure", "cypress": "woody_pure",
    "деревні ноти": "woody_pure", "woody notes": "woody_pure",

    # --- Mossy Woods / Chypre (woody_mossy) ---
    "дубовий мох": "woody_mossy", "мох": "woody_mossy", "oakmoss": "woody_mossy", "moss": "woody_mossy",
    "ладанник": "woody_mossy", "лабданум": "woody_mossy", "labdanum": "woody_mossy",
    "шипровий акорд": "woody_mossy", "chypre": "woody_mossy",

    # --- Dry Woods / Leather (woody_dry) ---
    "шкіра": "woody_dry", "шкіряний акорд": "woody_dry", "leather": "woody_dry",
    "тютюн": "woody_dry", "тютюну": "woody_dry", "tobacco": "woody_dry",
    "березовий дьоготь": "woody_dry", "береза": "woody_dry", "birch tar": "woody_dry",
    "замша": "woody_dry", "suede": "woody_dry",
    "димні ноти": "woody_dry", "дим": "woody_dry", "smoke": "woody_dry",

    # --- Citrus (fresh_citrus) ---
    "бергамот": "fresh_citrus", "бергамоту": "fresh_citrus", "bergamot": "fresh_citrus",
    "лимон": "fresh_citrus", "лимону": "fresh_citrus", "lemon": "fresh_citrus",
    "мандарин": "fresh_citrus", "мандарину": "fresh_citrus", "mandarin": "fresh_citrus", "tangerine": "fresh_citrus",
    "грейпфрут": "fresh_citrus", "grapefruit": "fresh_citrus",
    "лайм": "fresh_citrus", "lime": "fresh_citrus",
    "апельсин": "fresh_citrus", "orange": "fresh_citrus",
    "вербена": "fresh_citrus", "verbena": "fresh_citrus",
    "цитрусові ноти": "fresh_citrus", "цитруси": "fresh_citrus", "citrus": "fresh_citrus", "юдзу": "fresh_citrus", "yuzu": "fresh_citrus",

    # --- Water / Aquatic (fresh_aquatic) ---
    "морська сіль": "fresh_aquatic", "сіль": "fresh_aquatic", "sea salt": "fresh_aquatic",
    "морські ноти": "fresh_aquatic", "морський бриз": "fresh_aquatic", "marine notes": "fresh_aquatic", "sea notes": "fresh_aquatic",
    "калон": "fresh_aquatic", "calone": "fresh_aquatic",
    "водні ноти": "fresh_aquatic", "водяні ноти": "fresh_aquatic", "water notes": "fresh_aquatic", "aquatic notes": "fresh_aquatic",
    "озон": "fresh_aquatic", "ozone": "fresh_aquatic",
    "латаття": "fresh_aquatic", "водяна лілія": "fresh_aquatic", "water lily": "fresh_aquatic",

    # --- Green (fresh_green) ---
    "зелені ноти": "fresh_green", "green notes": "fresh_green",
    "скошена трава": "fresh_green", "трава": "fresh_green", "grass": "fresh_green",
    "гальбанум": "fresh_green", "galbanum": "fresh_green",
    "листя фіалки": "fresh_green", "violet leaf": "fresh_green",
    "м'ята": "fresh_green", "перцева м'ята": "fresh_green", "mint": "fresh_green", "peppermint": "fresh_green",
    "зелений чай": "fresh_green", "чай": "fresh_green", "green tea": "fresh_green", "tea": "fresh_green",
    "бамбук": "fresh_green", "bamboo": "fresh_green",

    # --- Fruity (fresh_fruity) ---
    "чорна смородина": "fresh_fruity", "смородина": "fresh_fruity", "blackcurrant": "fresh_fruity", "cassis": "fresh_fruity",
    "персик": "fresh_fruity", "peach": "fresh_fruity",
    "яблуко": "fresh_fruity", "apple": "fresh_fruity", "зелене яблуко": "fresh_fruity",
    "груша": "fresh_fruity", "pear": "fresh_fruity",
    "малина": "fresh_fruity", "raspberry": "fresh_fruity",
    "полуниця": "fresh_fruity", "суниця": "fresh_fruity", "strawberry": "fresh_fruity",
    "вишня": "fresh_fruity", "черешня": "fresh_fruity", "cherry": "fresh_fruity",
    "лічі": "fresh_fruity", "lychee": "fresh_fruity",
    "ананас": "fresh_fruity", "pineapple": "fresh_fruity",
    "слива": "fresh_fruity", "plum": "fresh_fruity",
    "гранат": "fresh_fruity", "pomegranate": "fresh_fruity",
    "кокос": "fresh_fruity", "coconut": "fresh_fruity",
    "фруктові ноти": "fresh_fruity", "fruity notes": "fresh_fruity",

    # --- Aromatic / Fougère (fresh_aromatic) ---
    "лаванда": "fresh_aromatic", "lavender": "fresh_aromatic",
    "розмарин": "fresh_aromatic", "rosemary": "fresh_aromatic",
    "шавлія": "fresh_aromatic", "мускатна шавлія": "fresh_aromatic", "sage": "fresh_aromatic", "clary sage": "fresh_aromatic",
    "базилік": "fresh_aromatic", "basil": "fresh_aromatic",
    "чебрець": "fresh_aromatic", "тим'ян": "fresh_aromatic", "thyme": "fresh_aromatic",
    "полин": "fresh_aromatic", "абсент": "fresh_aromatic", "wormwood": "fresh_aromatic",
    "ароматичні ноти": "fresh_aromatic", "фужерні ноти": "fresh_aromatic", "aromatic": "fresh_aromatic"
}


def clean_note_text(note_raw: str) -> str:
    """Очищує назву ноти від зайвих знаків, дужок тощо."""
    note = note_raw.lower().strip()
    note = re.sub(r"[\(\)\[\]\{\}\.,;:]", " ", note)
    note = re.sub(r"\s+", " ", note).strip()
    return note


def map_note_to_subfamily(note_str: str) -> Optional[str]:
    """
    Шукає збіг ноти у довіднику підгруп.
    Підтримує точний збіг та входження підрядка.
    """
    cleaned = clean_note_text(note_str)
    if not cleaned:
        return None

    # Прямий збіг
    if cleaned in NOTE_KEYWORD_MAP:
        return NOTE_KEYWORD_MAP[cleaned]

    # Пошук ключового слова всередині фрази (наприклад, "червона троянда" -> "троянда")
    for keyword, subfam in NOTE_KEYWORD_MAP.items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', cleaned):
            return subfam

    return None


def classify_pyramid(
    top_notes: List[str],
    heart_notes: List[str],
    base_notes: List[str],
    declared_family_hint: Optional[str] = None
) -> Tuple[Optional[str], Optional[str], Dict[str, float]]:
    """
    Аналізує ноти піраміди парфуму та визначає:
    1. primary_subfamily_id (головна підродина)
    2. primary_family_code (головне сімейство: floral, oriental, woody, fresh)
    3. ваговий профіль розподілу по підгрупах

    Ваги піраміди:
    - Base notes: вага 1.5 (стійка основа, шлейф)
    - Heart notes: вага 1.2 (ядро аромату)
    - Top notes: вага 0.7 (перші хвилини розкриття)
    """
    scores: Dict[str, float] = {sf["id"]: 0.0 for sf in SUBFAMILIES}

    levels = [
        (top_notes, 0.7),
        (heart_notes, 1.2),
        (base_notes, 1.5)
    ]

    matched_notes_count = 0

    for note_list, weight in levels:
        for note_raw in note_list:
            sf_id = map_note_to_subfamily(note_raw)
            if sf_id:
                scores[sf_id] += weight
                matched_notes_count += 1

    # Якщо була підказка від виробника/магазину (declared_family_hint)
    # Наприклад, "Деревні східні", "Водні фужерні", "Квіткові фруктові"
    if declared_family_hint:
        hint_clean = declared_family_hint.lower()
        family_weights = {
            "floral": ["квітков", "floral"],
            "oriental": ["східн", "орієнтальн", "amber", "oriental"],
            "woody": ["деревн", "шипров", "шкірян", "woody"],
            "fresh": ["свіж", "водн", "акватичн", "цитрус", "фужерн", "fresh", "aquatic"]
        }
        for fam_code, keywords in family_weights.items():
            if any(kw in hint_clean for kw in keywords):
                for sf in SUBFAMILIES:
                    if sf["family_code"] == fam_code:
                        scores[sf["id"]] += 1.5

        # Точніший мапінг підродини з підказки
        subfam_keywords = {
            "fresh_aquatic": ["водн", "акватичн", "морськ", "aquatic", "marine"],
            "fresh_citrus": ["цитрус", "citrus"],
            "fresh_fruity": ["фрукт", "ягідн", "fruity"],
            "fresh_aromatic": ["фужерн", "ароматичн", "aromatic", "foug"],
            "woody_pure": ["деревн", "woody", "woods"],
            "woody_mossy": ["мохов", "шипров", "chypre"],
            "woody_dry": ["шкірян", "сух", "тютюн", "leather"],
            "oriental_woody": ["деревно-східн", "східно-деревн"],
            "floral_oriental": ["квітково-східн", "східно-квітков"],
            "floral_soft": ["м'які квітков", "пудров"],
            "floral_pure": ["квітков", "floral"]
        }
        for sf_id, kws in subfam_keywords.items():
            if any(kw in hint_clean for kw in kws):
                scores[sf_id] += 2.0

    # Знаходимо лідера
    best_subfam = None
    max_score = 0.0
    for sf_id, score in scores.items():
        if score > max_score:
            max_score = score
            best_subfam = sf_id

    # Якщо збігів немає взагалі
    if max_score <= 0.0:
        return None, None, scores

    best_family = SUBFAMILIES_BY_ID[best_subfam]["family_code"]
    return best_subfam, best_family, scores
