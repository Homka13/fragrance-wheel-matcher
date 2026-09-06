"""
generate_d1_seed.py
Генерує SQL-дамп seed_d1.sql для завантаження в Cloudflare D1.
"""

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.wheel_topology import FAMILIES, SUBFAMILIES

def generate():
    embedded_file = PROJECT_ROOT / "data" / "embedded_products.json"
    with open(embedded_file, "r", encoding="utf-8") as f:
        products = json.load(f)

    lines = ["-- Cloudflare D1 Seed Script (18 Bestsellers & Reference Tables)\n"]

    # 1. Families
    for code, fam in FAMILIES.items():
        p = fam["profile"].replace("'", "''")
        n_uk = fam["name_uk"].replace("'", "''")
        n_en = fam["name_en"].replace("'", "''")
        lines.append(f"INSERT OR REPLACE INTO wheel_families (code, name_uk, name_en, color_hex, profile) VALUES ('{code}', '{n_uk}', '{n_en}', '{fam['color_hex']}', '{p}');")

    lines.append("\n-- 2. Subfamilies")

    # 2. Subfamilies
    for sf in SUBFAMILIES:
        p = sf["profile"].replace("'", "''")
        n_uk = sf["name_uk"].replace("'", "''")
        n_en = sf["name_en"].replace("'", "''")
        ingredients = json.dumps(sf["key_ingredients"], ensure_ascii=False).replace("'", "''")
        lines.append(f"INSERT OR REPLACE INTO wheel_subfamilies (id, ring_index, family_code, name_uk, name_en, color_hex, profile, key_ingredients) VALUES ('{sf['id']}', {sf['ring_index']}, '{sf['family_code']}', '{n_uk}', '{n_en}', '{sf['color_hex']}', '{p}', '{ingredients}');")

    lines.append("\n-- 3. Brands")

    # 3. Brands
    brands = {}
    for p in products:
        brands[p["brand_id"]] = p["brand_name"]

    for b_id, b_name in sorted(brands.items()):
        bn = b_name.replace("'", "''")
        lines.append(f"INSERT OR REPLACE INTO brands (id, name) VALUES ('{b_id}', '{bn}');")

    lines.append("\n-- 4. Fragrances")

    # 4. Fragrances
    for p in products:
        f_id = p["id"]
        b_id = p["brand_id"]
        b_name = p["brand_name"].replace("'", "''")
        name = p["name"].replace("'", "''")
        gender = p.get("gender", "unisex")
        conc = p.get("concentration", "Eau de Parfum").replace("'", "''")
        sf_id = p["primary_subfamily_id"]
        fam_code = p["family_code"]
        top = json.dumps(p.get("top_notes", []), ensure_ascii=False).replace("'", "''")
        heart = json.dumps(p.get("heart_notes", []), ensure_ascii=False).replace("'", "''")
        base = json.dumps(p.get("base_notes", []), ensure_ascii=False).replace("'", "''")
        price = p.get("price_uah") or "NULL"
        sku = f"'{p['product_sku']}'" if p.get("product_sku") else "NULL"
        url = f"'{p['product_url']}'" if p.get("product_url") else "NULL"
        img = f"'{p['image_url']}'" if p.get("image_url") else "NULL"

        lines.append(f"INSERT OR REPLACE INTO fragrances (id, brand_id, brand_name, name, gender, concentration, primary_subfamily_id, family_code, top_notes, heart_notes, base_notes, price_uah, product_sku, product_url, image_url) VALUES ('{f_id}', '{b_id}', '{b_name}', '{name}', '{gender}', '{conc}', '{sf_id}', '{fam_code}', '{top}', '{heart}', '{base}', {price}, {sku}, {url}, {img});")

    out_file = PROJECT_ROOT / "cloudflare_worker" / "seed_d1.sql"
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Generated {out_file} successfully! ({len(products)} products)")

if __name__ == "__main__":
    generate()
