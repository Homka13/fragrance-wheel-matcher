"""
catalog_scraper.py
Модуль парсингу каталогу та ольфакторних пірамід парфумерії.
Включає:
1. HTML-парсер описів пірамід («Початкова нота», «Нота серця», «Кінцева нота»).
2. Playwright-раннер для автоматизованого збору даних у браузерному режимі.
"""

import re
import json
import logging
from typing import Dict, List, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger("catalog_scraper")


def extract_pyramid_from_text(description_text: str) -> Dict[str, List[str]]:
    """
    Витягує ноти піраміди зі стандартного опису парфуму в e-commerce каталогах.
    Шукає маркери:
    - Початкова нота / Верхні ноти
    - Нота серця / Середні ноти
    - Кінцева нота / Базові ноти
    """
    pyramid = {
        "top_notes": [],
        "heart_notes": [],
        "base_notes": []
    }

    if not description_text:
        return pyramid

    # Нормалізація тексту
    text = description_text.replace("\xa0", " ")

    # Регулярні вирази для секцій піраміди
    top_match = re.search(r"(?:початков[аі]\s+нот[аи]|верхні\s+ноти)\s*[:\-–]\s*([^;\.\n\r]+)", text, re.IGNORECASE)
    heart_match = re.search(r"(?:нот[аи]\s+серця|середні\s+ноти)\s*[:\-–]\s*([^;\.\n\r]+)", text, re.IGNORECASE)
    base_match = re.search(r"(?:кінцев[аі]\s+нот[аи]|базов[іа]\s+ноти|шлейф)\s*[:\-–]\s*([^;\.\n\r]+)", text, re.IGNORECASE)

    def split_notes(notes_str: str) -> List[str]:
        # Розбиваємо за комами, крапками з комою або "та"
        parts = re.split(r"[,;]|\s+та\s+|\s+і\s+", notes_str)
        cleaned = []
        for p in parts:
            c = p.strip().strip(".").lower()
            if c and len(c) > 1:
                cleaned.append(c)
        return cleaned

    if top_match:
        pyramid["top_notes"] = split_notes(top_match.group(1))
    if heart_match:
        pyramid["heart_notes"] = split_notes(heart_match.group(1))
    if base_match:
        pyramid["base_notes"] = split_notes(base_match.group(1))

    return pyramid


def parse_product_html(html_content: str, url: Optional[str] = None) -> Optional[Dict]:
    """
    Парсить сторінку товару парфумерії (збережений HTML або DOM)
    та повертає стандартизовану структуру для Data Contract.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Пошук назви та бренду
    title_elem = soup.find("h1") or soup.find(class_=re.compile(r"product.*title|title", re.I))
    if not title_elem:
        return None

    full_title = title_elem.get_text(strip=True)

    # Бренд
    brand_elem = soup.find(class_=re.compile(r"brand|vendor", re.I))
    brand_name = brand_elem.get_text(strip=True) if brand_elem else "Unknown"

    # Якщо бренд у заголовку
    clean_name = full_title
    if brand_name != "Unknown" and brand_name.lower() in full_title.lower():
        clean_name = re.sub(re.escape(brand_name), "", full_title, flags=re.I).strip(" -—")

    # Концентрація (EDP, EDT тощо)
    concentration = "EDP"
    if "туалетна вода" in full_title.lower() or "edt" in full_title.lower():
        concentration = "EDT"
    elif "парфумована вода" in full_title.lower() or "edp" in full_title.lower():
        concentration = "EDP"
    elif "духи" in full_title.lower() or "extrait" in full_title.lower():
        concentration = "Extrait"

    # Пошук опису піраміди
    desc_elem = soup.find(class_=re.compile(r"description|details|composition", re.I))
    desc_text = desc_elem.get_text(separator=" ", strip=True) if desc_elem else soup.get_text()
    pyramid = extract_pyramid_from_text(desc_text)

    # Ціна
    price = None
    price_elem = soup.find(class_=re.compile(r"price.*current|current.*price|price", re.I))
    if price_elem:
        raw_price = re.sub(r"[^\d]", "", price_elem.get_text())
        if raw_price:
            price = float(raw_price)

    # SKU або артикул
    sku = None
    sku_elem = soup.find(text=re.compile(r"артикул|код", re.I))
    if sku_elem and sku_elem.parent:
        sku = sku_elem.parent.get_text(strip=True)

    # ID для парфуму
    slug_id = re.sub(r"[^\w\s-]", "", f"{brand_name}_{clean_name}").strip().lower()
    slug_id = re.sub(r"[\s_-]+", "_", slug_id)

    return {
        "id": slug_id,
        "name": clean_name or full_title,
        "brand_name": brand_name,
        "gender": "unisex",
        "concentration": concentration,
        "top_notes": pyramid["top_notes"],
        "heart_notes": pyramid["heart_notes"],
        "base_notes": pyramid["base_notes"],
        "price_uah": price,
        "product_sku": sku,
        "product_url": url,
        "declared_family": None
    }


async def run_playwright_scraper(target_urls: List[str], output_json_path: str):
    """
    Запуск Playwright браузера для автоматичного збору карток товарів
    з онлайн-каталогів парфумерії.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("Playwright не встановлено. Встановіть через: pip install playwright && playwright install chromium")
        return []

    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for url in target_urls:
            try:
                logger.info(f"Відкриваємо: {url}")
                await page.goto(url, wait_until="networkidle", timeout=45000)
                await page.wait_for_timeout(3000)

                html = await page.content()
                item = parse_product_html(html, url=url)
                if item:
                    results.append(item)
                    logger.info(f"Успішно зібрано: {item['brand_name']} - {item['name']}")
            except Exception as e:
                logger.error(f"Помилка при зборі {url}: {e}")

        await browser.close()

    if results:
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump({"products": results}, f, ensure_ascii=False, indent=2)
        logger.info(f"Збережено {len(results)} парфумів у {output_json_path}")

    return results


DEFAULT_BROCARD_TARGETS = [
    "https://www.brocard.ua/ua/product/parfumovana-voda-lancome-la-vie-est-belle",
    "https://www.brocard.ua/ua/product/parfumovana-voda-lancome-idole",
    "https://www.brocard.ua/ua/product/parfumovana-voda-lancome-tresor",
    "https://www.brocard.ua/ua/product/parfumovana-voda-carolina-herrera-good-girl",
    "https://www.brocard.ua/ua/product/parfumovana-voda-carolina-herrera-very-good-girl",
    "https://www.brocard.ua/ua/product/tualetna-voda-carolina-herrera-bad-boy",
    "https://www.brocard.ua/ua/product/chanel-coco-mademoiselle",
    "https://www.brocard.ua/ua/product/chanel-bleu-de-chanel",
    "https://www.brocard.ua/ua/product/tom-ford-tobacco-vanille",
    "https://www.brocard.ua/ua/product/tom-ford-oud-wood",
    "https://www.brocard.ua/ua/product/tom-ford-lost-cherry",
    "https://www.brocard.ua/ua/product/yves-saint-laurent-black-opium",
    "https://www.brocard.ua/ua/product/yves-saint-laurent-libre",
    "https://www.brocard.ua/ua/product/dior-sauvage",
    "https://www.brocard.ua/ua/product/dior-fahrenheit",
    "https://www.brocard.ua/ua/product/giorgio-armani-acqua-di-gio",
    "https://www.brocard.ua/ua/product/maison-francis-kurkdjian-baccarat-rouge-540",
    "https://www.brocard.ua/ua/product/kilian-angels-share"
]

if __name__ == "__main__":
    import asyncio
    output_file = "data/scraped_catalog.json"
    print("Запуск скрапера для збору карток з каталогу Brocard...")
    asyncio.run(run_playwright_scraper(DEFAULT_BROCARD_TARGETS, output_file))
