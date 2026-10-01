"""
test_brocard_scraper.py
Тести для модуля парсингу Brocard.ua та валідації зібраних даних.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scrapers.brocard_scraper import BrocardScraper
from core.pyramid_classifier import classify_pyramid
from pipeline.ingest import process_and_ingest_records
from db.database import init_db, get_db
from db.models import FragranceModel


def test_brocard_data_parsing():
    from bs4 import BeautifulSoup
    scraper = BrocardScraper(headless=True)

    dummy_html = """
    <html>
        <body>
            <h1>DIOR Sauvage парфумована вода</h1>
            <div class="product-brand">DIOR</div>
            <ul>
                <li class="product-attribute">
                    <strong class="attribute-name">Стать</strong>
                    <span class="attribute-label">для чоловіків</span>
                </li>
                <li class="product-attribute">
                    <strong class="attribute-name">Група ароматів</strong>
                    <span class="attribute-label">деревний</span>
                </li>
                <li class="product-attribute">
                    <strong class="attribute-name">Ноти</strong>
                    <span class="attribute-label">бергамот</span>
                    <span class="attribute-label">перець</span>
                    <span class="attribute-label">амброксан</span>
                </li>
            </ul>
            <div class="price-box">
                <span class="price">4 500,00 ₴</span>
            </div>
            <img src="https://www.brocard.ua/media/catalog/product/d/i/dior_sauvage.jpg" />
        </body>
    </html>
    """

    soup = BeautifulSoup(dummy_html, "html.parser")
    res = scraper._parse_soup(
        soup=soup,
        url="https://www.brocard.ua/ua/product/dior-sauvage-12345",
        default_gender="male"
    )

    assert res is not None
    assert "sauvage" in res["name"].lower()
    assert res["brand_name"] == "DIOR"
    assert res["gender"] == "male"
    assert res["price_uah"] == 4500.0
    assert "бергамот" in res["top_notes"] or "бергамот" in (res["top_notes"] + res["heart_notes"] + res["base_notes"])

    # Перевіряємо класифікацію піраміди
    subfam, fam_code, _ = classify_pyramid(res["top_notes"], res["heart_notes"], res["base_notes"], res["declared_family"])
    assert subfam is not None
    print(f"test_brocard_data_parsing: PASSED (Subfamily={subfam}, Family={fam_code})")


def test_duckdb_bulk_ingest():
    init_db()

    items = [
        {
            "id": "brocard_test_perfume_f",
            "name": "La Nuit Florale",
            "brand_name": "Lancôme",
            "gender": "female",
            "concentration": "Eau de Parfum",
            "declared_family": "Квіткові",
            "top_notes": ["півонія"],
            "heart_notes": ["троянда"],
            "base_notes": ["мускус"],
            "price_uah": 3200.0,
            "product_url": "https://www.brocard.ua/ua/product/test-f"
        },
        {
            "id": "brocard_test_perfume_m",
            "name": "Bois Intense",
            "brand_name": "Tom Ford",
            "gender": "male",
            "concentration": "Eau de Parfum",
            "declared_family": "Деревні",
            "top_notes": ["бергамот"],
            "heart_notes": ["кардамон"],
            "base_notes": ["уд", "кедр"],
            "price_uah": 6500.0,
            "product_url": "https://www.brocard.ua/ua/product/test-m"
        },
        {
            "id": "brocard_test_perfume_u",
            "name": "Santal Noir",
            "brand_name": "Maison Francis Kurkdjian",
            "gender": "unisex",
            "concentration": "Extrait de Parfum",
            "declared_family": "Східні",
            "top_notes": ["шафран"],
            "heart_notes": ["сандал"],
            "base_notes": ["амбра", "ваніль"],
            "price_uah": 8900.0,
            "product_url": "https://www.brocard.ua/ua/product/test-u"
        }
    ]

    res = process_and_ingest_records(items, update_cache=False)
    assert res["upserted"] == 3
    assert res["skipped_count"] == 0

    with get_db() as session:
        f = session.query(FragranceModel).filter_by(id="brocard_test_perfume_f").first()
        assert f is not None
        assert f.gender == "female"
        assert f.price_uah == 3200.0

        m = session.query(FragranceModel).filter_by(id="brocard_test_perfume_m").first()
        assert m is not None
        assert m.gender == "male"

        u = session.query(FragranceModel).filter_by(id="brocard_test_perfume_u").first()
        assert u is not None
        assert u.gender == "unisex"

    print("test_duckdb_bulk_ingest: PASSED")


if __name__ == "__main__":
    test_brocard_data_parsing()
    test_duckdb_bulk_ingest()
