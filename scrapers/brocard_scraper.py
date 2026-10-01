"""
brocard_scraper.py
Повноцінний скрапер каталогу парфумерії інтернет-магазину Brocard.ua.
Збирає жіночі, чоловічі та унісекс аромати з ольфакторними нотами, цінами, брендами та фото.
Використовує реальний браузер (Brave / Chromium) з антидетектом для автоматичного проходження Cloudflare.
"""

import os
import re
import json
import time
import logging
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from patchright.async_api import async_playwright, Browser, BrowserContext, Page

try:
    from scrapers.catalog_scraper import extract_pyramid_from_text
    from pipeline.ingest import process_and_ingest_records, slugify_brand
    from core.pyramid_classifier import classify_pyramid
    from db.database import init_db, sync_to_sqlite
except ImportError:
    from catalog_scraper import extract_pyramid_from_text
    from ..pipeline.ingest import process_and_ingest_records, slugify_brand
    from ..core.pyramid_classifier import classify_pyramid
    from ..db.database import init_db, sync_to_sqlite

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("brocard_scraper")

BASE_URL = "https://www.brocard.ua"

CATEGORY_URLS = {
    "female": "https://www.brocard.ua/ua/category/aromati-dlya-nei",
    "male": "https://www.brocard.ua/ua/category/aromati-dlya-nogo",
    "unisex": "https://www.brocard.ua/ua/category/nisheva-parfyumeriya"
}

BRAVE_PATH = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"


class BrocardScraper:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def start_browser(self):
        """Ініціалізація браузера та проходження початкової перевірки Cloudflare."""
        self.playwright = await async_playwright().start()

        launch_args = {
            "headless": self.headless,
            "args": ["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        }
        if os.path.exists(BRAVE_PATH):
            logger.info(f"Використовуємо системний браузер: {BRAVE_PATH}")
            launch_args["executable_path"] = BRAVE_PATH
        else:
            logger.info("Використовуємо Chromium")

        self.browser = await self.playwright.chromium.launch(**launch_args)
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800}
        )
        self.page = await self.context.new_page()

        logger.info("Відкриваємо головну сторінку Brocard для проходження Cloudflare перевірки...")
        await self.page.goto(f"{BASE_URL}/ua", wait_until="domcontentloaded", timeout=45000)

        # Очікуємо проходження перевірки
        start = time.time()
        passed = False
        while time.time() - start < 20:
            await self.page.wait_for_timeout(1000)
            try:
                title = await self.page.title()
                if "Трохи зачекайте" not in title and "Just a moment" not in title and len(title) > 5:
                    logger.info(f"Cloudflare успішно пройдено за {round(time.time() - start, 1)}с! Заголовок: {title}")
                    passed = True
                    break
            except Exception:
                pass

        if not passed:
            logger.warning("Очікування проходження перевірки триває довше звичайного, продовжуємо...")

        await self.page.wait_for_timeout(1500)
        return True

    async def close_browser(self):
        """Закриття браузера."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def collect_category_links(
        self, category_key: str, count: int, exclude_urls: Optional[Set[str]] = None
    ) -> List[str]:
        """
        Збирає посилання на сторінки товарів для певної категорії (пагінація: /page-1, /page-2...).
        Підтримує виключення вже існуючих товарів (exclude_urls) та перехід на наступні сторінки.
        """
        cat_url = CATEGORY_URLS.get(category_key)
        if not cat_url:
            raise ValueError(f"Невідома категорія: {category_key}")

        collected: List[str] = []
        seen: Set[str] = set()
        page_num = 1

        logger.info(f"Збір посилань для '{category_key.upper()}' (необхідно нових: {count})...")

        while len(collected) < count and page_num <= 25:
            page_url = f"{cat_url}/page-{page_num}" if page_num > 1 else cat_url
            logger.info(f"  Завантаження сторінки каталогу {page_num}: {page_url}")

            try:
                await self.page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
                await self.page.wait_for_timeout(2000)

                # Перевіряємо, чи сторінка не застрягла на челенджі
                for _ in range(5):
                    t = await self.page.title()
                    if "Трохи зачекайте" not in t and "Just a moment" not in t:
                        break
                    await self.page.wait_for_timeout(1000)

                # Чекаємо появи посилань на товари в DOM
                try:
                    await self.page.wait_for_selector("a[href*='/product/']", timeout=10000)
                except Exception:
                    pass

                await self.page.wait_for_timeout(1500)
                html = await self.page.content()
                soup = BeautifulSoup(html, "html.parser")

                page_product_links = []
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if "/product/" in href:
                        full_href = urljoin(BASE_URL, href.split("?")[0].split("#")[0])
                        page_product_links.append(full_href)

                if not page_product_links:
                    logger.info(f"  На сторінці {page_num} відсутні посилання на товари. Завершуємо категорію.")
                    break

                new_count_on_page = 0
                for full_href in page_product_links:
                    if full_href not in seen and (exclude_urls is None or full_href not in exclude_urls):
                        seen.add(full_href)
                        collected.append(full_href)
                        new_count_on_page += 1
                        if len(collected) >= count:
                            break

                logger.info(
                    f"  Сторінка {page_num}: знайдено {new_count_on_page} нових карток "
                    f"(всього зібрано: {len(collected)}/{count})"
                )
                page_num += 1
                await self.page.wait_for_timeout(1000)

            except Exception as e:
                logger.error(f"Помилка при завантаженні {page_url}: {e}")
                break

        return collected

    async def parse_product(self, url: str, default_gender: str = "unisex") -> Optional[Dict]:
        """
        Відкриває картку товару в браузері та витягує всі параметри для Колеса Ароматів і БД.
        """
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(1500)

            # Перевіряємо заголовок сторінки
            for _ in range(5):
                t = await self.page.title()
                if "Трохи зачекайте" not in t and "Just a moment" not in t:
                    break
                await self.page.wait_for_timeout(1000)

            html = await self.page.content()
            soup = BeautifulSoup(html, "html.parser")
            return self._parse_soup(soup, url=url, default_gender=default_gender)
        except Exception as e:
            logger.error(f"Помилка завантаження сторінки {url}: {e}")
            return None

    def _parse_soup(self, soup: BeautifulSoup, url: str, default_gender: str = "unisex") -> Optional[Dict]:
        """
        Витягує всі параметри парфуму для Колеса Ароматів та БД з об'єкта BeautifulSoup.
        """
        try:
            # Назва товару
            h1_el = soup.find("h1")
            full_title = h1_el.get_text(separator=" ", strip=True) if h1_el else ""

            # Бренд
            brand_el = soup.find(class_=re.compile(r"brand", re.I))
            brand_name = brand_el.get_text(strip=True) if brand_el else ""

            # Якщо окремого елементу бренду немає, витягуємо з breadcrumbs
            if not brand_name:
                bc = soup.find(class_=re.compile(r"breadcrumbs|nav", re.I))
                if bc:
                    m = re.search(r"brands/([^/]+)", str(bc))
                    if m:
                        brand_name = m.group(1).replace("-", " ").title()

            # Якщо і там немає, беремо перше слово з H1
            if not brand_name and full_title:
                brand_name = full_title.split()[0]

            # Очищуємо назву парфуму
            clean_name = full_title
            if brand_name and brand_name.lower() in clean_name.lower():
                clean_name = re.sub(re.escape(brand_name), "", clean_name, flags=re.I).strip(" -—:\n\r\t")
            if not clean_name:
                clean_name = full_title or "Fragrance"

            # 1. Характеристики з DOM через li.product-attribute
            specs = {}
            for attr_li in soup.select("li.product-attribute, .spec-item"):
                name_el = attr_li.select_one(".attribute-name, strong")
                if not name_el:
                    continue
                k = name_el.get_text(strip=True).strip(":").lower()
                
                # Значення: збираємо список з .attribute-label або текст
                labels = [l.get_text(strip=True) for l in attr_li.select(".attribute-label") if l.get_text(strip=True)]
                if labels:
                    specs[k] = labels
                else:
                    val_el = attr_li.select_one(".attribute-value") or attr_li
                    v_text = val_el.get_text(separator=" ", strip=True).replace(name_el.get_text(strip=True), "").strip()
                    specs[k] = [v_text] if v_text else []

            # Стать
            gender_list = specs.get("стать", [])
            gender_raw = " ".join(gender_list).lower()
            if ("жінок" in gender_raw or "жіноч" in gender_raw) and ("чоловік" in gender_raw):
                gender = "unisex"
            elif default_gender == "unisex":
                gender = "unisex"
            elif "жінок" in gender_raw or "жіноч" in gender_raw:
                gender = "female"
            elif "чоловік" in gender_raw:
                gender = "male"
            elif "унісекс" in gender_raw or "unisex" in gender_raw:
                gender = "unisex"
            else:
                gender = default_gender

            # Задекларована група ароматів
            declared_family_list = specs.get("група ароматів", [])
            declared_family = ", ".join(declared_family_list) if declared_family_list else None

            # Ноти піраміди
            raw_notes = specs.get("ноти", [])

            # Опис піраміди
            desc_el = soup.select_one(".product-description, [class*='description'], .product-about")
            desc_text = desc_el.get_text(separator=" ", strip=True) if desc_el else soup.get_text()
            pyramid = extract_pyramid_from_text(desc_text)

            # Якщо опис не містить початкові/серцеві/базові, розподіляємо наявні ноти
            if not (pyramid["top_notes"] or pyramid["heart_notes"] or pyramid["base_notes"]) and raw_notes:
                if len(raw_notes) >= 3:
                    pyramid["top_notes"] = [raw_notes[0].lower()]
                    pyramid["heart_notes"] = [n.lower() for n in raw_notes[1:-1]]
                    pyramid["base_notes"] = [raw_notes[-1].lower()]
                else:
                    pyramid["top_notes"] = [n.lower() for n in raw_notes[:1]]
                    pyramid["heart_notes"] = [n.lower() for n in raw_notes[1:]]

            # Концентрація
            t_low = full_title.lower()
            if "парфумована вода" in t_low or "eau de parfum" in t_low or "edp" in t_low:
                concentration = "Eau de Parfum"
            elif "туалетна вода" in t_low or "eau de toilette" in t_low or "edt" in t_low:
                concentration = "Eau de Toilette"
            elif "духи" in t_low or "extrait" in t_low:
                concentration = "Extrait de Parfum"
            elif "одеколон" in t_low or "edc" in t_low:
                concentration = "Eau de Cologne"
            else:
                concentration = "Eau de Parfum"

            # Ціна (UAH)
            price = None
            price_el = soup.select_one(".price-box .special-price .price, .price-box .price, .price-format .price, .price")
            if price_el:
                raw_price = re.sub(r"[^\d,\.]", "", price_el.get_text().replace(" ", "").replace("\xa0", ""))
                raw_price = raw_price.replace(",", ".")
                try:
                    price = float(raw_price)
                except ValueError:
                    pass

            if price is None:
                price_matches = re.findall(r"(\d+[\s\d]*,\d+)\s*₴", html)
                if price_matches:
                    clean_prices = []
                    for pm in price_matches:
                        digits = pm.replace(" ", "").replace("\xa0", "").replace(",", ".")
                        try:
                            clean_prices.append(float(digits))
                        except ValueError:
                            pass
                    if clean_prices:
                        price = min(clean_prices)

            # Артикул / Код товару
            sku = None
            code_el = soup.find(string=re.compile(r"Код товара|Артикул", re.I))
            if code_el and code_el.parent:
                sku_raw = code_el.parent.get_text(strip=True)
                sku_match = re.search(r"[A-Za-z0-9_-]{5,15}", sku_raw)
                if sku_match:
                    sku = sku_match.group(0)

            if not sku:
                sku_from_url = re.search(r"(\d{5,8})", url)
                sku = sku_from_url.group(1) if sku_from_url else None

            b_slug = slugify_brand(brand_name)
            n_slug = re.sub(r"[^\w\s-]", "", clean_name.lower()).strip()
            n_slug = re.sub(r"[\s_-]+", "_", n_slug)
            if sku:
                clean_sku = re.sub(r"[^\w-]", "", str(sku).lower())
                prod_id = f"{b_slug}_{n_slug}_{clean_sku}"[:75].strip("_")
            else:
                prod_id = f"{b_slug}_{n_slug}"[:75].strip("_")
                sku = prod_id

            # Головне зображення
            image_url = None
            img_el = soup.find("img", src=re.compile(r"media/catalog/product"))
            if img_el:
                image_url = img_el.get("src") or img_el.get("data-src")
                if image_url and not image_url.startswith("http"):
                    image_url = urljoin(BASE_URL, image_url)

            return {
                "id": prod_id,
                "name": clean_name,
                "brand_name": brand_name,
                "brand_id": b_slug,
                "gender": gender,
                "concentration": concentration,
                "declared_family": declared_family,
                "top_notes": pyramid["top_notes"],
                "heart_notes": pyramid["heart_notes"],
                "base_notes": pyramid["base_notes"],
                "price_uah": price,
                "product_sku": sku,
                "product_url": url,
                "image_url": image_url
            }

        except Exception as e:
            logger.error(f"Помилка парсингу сторінки {url}: {e}")
            return None

    async def scrape_catalog(self, targets: Dict[str, int]) -> List[Dict]:
        """
        Головний метод виконання збору за цільовими категоріями.
        """
        await self.start_browser()
        all_products: List[Dict] = []
        seen_urls: Set[str] = set()

        # Отримуємо вже збережені URL з DuckDB, щоб не збирати дублікати
        existing_urls: Set[str] = set()
        try:
            import duckdb
            con = duckdb.connect("fragrances.duckdb")
            rows = con.execute("SELECT product_url FROM fragrances WHERE product_url IS NOT NULL").fetchall()
            existing_urls = {r[0] for r in rows if r[0]}
            con.close()
            logger.info(f"Знайдено {len(existing_urls)} існуючих парфумів у DuckDB, вони будуть пропущені при зборі.")
        except Exception as e:
            logger.warning(f"Не вдалося зчитати існуючі URL з DuckDB: {e}")

        try:
            for cat_key, target_count in targets.items():
                if target_count <= 0:
                    continue
                logger.info(f"\n==========================================")
                logger.info(f"ПОЧАТОК ЗБОРУ КАТЕГОРІЇ: {cat_key.upper()} (Ціль нових: {target_count})")
                logger.info(f"==========================================")

                # Збираємо посилання з великим запасом, оскільки в чоловічій секції багато нішевих унісекс
                target_buffer = max(80, target_count * 5 + 20) if cat_key == "male" else (target_count * 2 + 15)
                links = await self.collect_category_links(cat_key, count=target_buffer, exclude_urls=existing_urls)
                cat_products: List[Dict] = []

                for i, link in enumerate(links, 1):
                    if len(cat_products) >= target_count:
                        break
                    if link in seen_urls or link in existing_urls:
                        continue
                    seen_urls.add(link)

                    logger.info(f"[{cat_key.upper()}] ({len(cat_products)+1}/{target_count}) Парсимо: {link}")
                    item = await self.parse_product(link, default_gender=cat_key)

                    # Перевіряємо, чи є хоча б якісь ноти або група для валідації
                    all_notes = (item.get("top_notes", []) + item.get("heart_notes", []) + item.get("base_notes", [])) if item else []
                    if item and (all_notes or item.get("declared_family")):
                        existing_urls.add(link)
                        if item.get("gender") == cat_key or cat_key == "unisex":
                            cat_products.append(item)
                        else:
                            all_products.append(item)
                        logger.info(
                            f"  -> Зібрано: {item['brand_name']} - {item['name']} | "
                            f"Ціна: {item['price_uah']} грн | "
                            f"Стать: {item['gender']} | "
                            f"Ноти ({len(all_notes)}): {', '.join(all_notes[:4])}"
                        )
                    else:
                        logger.warning(f"  -> Пропущено: відсутні ольфакторні ноти або опис товару.")

                    await self.page.wait_for_timeout(800)

                logger.info(f"Категорію {cat_key.upper()} завершено: зібрано {len(cat_products)}/{target_count}")
                all_products.extend(cat_products)

        finally:
            await self.close_browser()

        return all_products


async def run_scraper_cli(targets: Dict[str, int], output_file: str, headless: bool = False, skip_db: bool = False):
    scraper = BrocardScraper(headless=headless)
    new_products = await scraper.scrape_catalog(targets)

    # Зберігаємо або доповнюємо загальний JSON файл
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    all_combined = []
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                all_combined = old_data.get("products", [])
        except Exception:
            all_combined = []

    existing_urls_json = {p.get("product_url") for p in all_combined if p.get("product_url")}
    for p in new_products:
        if p.get("product_url") not in existing_urls_json:
            all_combined.append(p)
            existing_urls_json.add(p.get("product_url"))

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"products": all_combined, "count": len(all_combined)}, f, ensure_ascii=False, indent=2)
    logger.info(f"Дані збережено у файл: {output_file} (всього в JSON: {len(all_combined)}, нових додано: {len(new_products)})")

    # Завантажуємо нові парфуми в DuckDB / SQLite
    if not skip_db and new_products:
        logger.info("Завантаження нових позицій в базу даних (DuckDB)...")
        init_db()
        summary = process_and_ingest_records(new_products, update_cache=False)
        logger.info(f"Підсумок імпорту: {summary}")

        # Синхронізуємо з SQLite для DB Browser
        try:
            sync_to_sqlite()
            logger.info("Синхронізація з SQLite успішна.")
        except Exception as e:
            logger.warning(f"Синхронізація з SQLite: {e}")

    return new_products
