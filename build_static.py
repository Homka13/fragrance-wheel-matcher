"""
build_static.py
Генерує версію index.html з вбудованими даними для GitHub Pages та standalone режиму.
"""

import json
from pathlib import Path
from core.wheel_topology import FAMILIES, SUBFAMILIES

BASE_DIR = Path(__file__).resolve().parent

def build():
    json_path = BASE_DIR / "data" / "embedded_products.json"
    if not json_path.exists():
        print("embedded_products.json not found")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    # Читаємо поточний index.html
    src_html = BASE_DIR / "app" / "static" / "index.html"
    content = src_html.read_text(encoding="utf-8")

    # Додаємо копії для GitHub Pages
    (BASE_DIR / "docs").mkdir(exist_ok=True)
    (BASE_DIR / "docs" / "index.html").write_text(content, encoding="utf-8")
    (BASE_DIR / "index.html").write_text(content, encoding="utf-8")
    print("Static files synchronized for GitHub Pages!")

if __name__ == "__main__":
    build()
