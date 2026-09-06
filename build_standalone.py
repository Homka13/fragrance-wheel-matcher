"""
build_standalone.py
Вбудовує повні дані каталогу парфумерії та клієнтський рушій метчингу в index.html,
завдяки чому додаток працює як з бекендом FastAPI/Starlette, так і на GitHub Pages.
"""

import json
import re
from pathlib import Path
from core.wheel_topology import FAMILIES, SUBFAMILIES
from core.pyramid_classifier import classify_pyramid

BASE_DIR = Path(__file__).resolve().parent

def run_build():
    seed_path = BASE_DIR / "data" / "seed_catalog.json"
    with open(seed_path, "r", encoding="utf-8") as f:
        seed_data = json.load(f)

    # Генерація валідованих парфумів для вбудовування
    products = []
    for item in seed_data.get("products", []):
        primary_subfam, family_code, _ = classify_pyramid(
            top_notes=item.get("top_notes", []),
            heart_notes=item.get("heart_notes", []),
            base_notes=item.get("base_notes", []),
            declared_family_hint=item.get("declared_family")
        )
        products.append({
            "id": item["id"],
            "brand_id": item.get("brand_id", item["brand_name"].lower()),
            "brand_name": item["brand_name"],
            "name": item["name"],
            "gender": item.get("gender", "unisex"),
            "concentration": item.get("concentration", "EDP"),
            "primary_subfamily_id": primary_subfam,
            "family_code": family_code,
            "top_notes": item.get("top_notes", []),
            "heart_notes": item.get("heart_notes", []),
            "base_notes": item.get("base_notes", []),
            "price_uah": item.get("price_uah"),
            "product_sku": item.get("product_sku"),
            "product_url": item.get("product_url", "#"),
            "image_url": item.get("image_url")
        })

    json_path = BASE_DIR / "data" / "embedded_products.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    src_html = BASE_DIR / "app" / "static" / "index.html"
    content = src_html.read_text(encoding="utf-8")

    families_js = json.dumps(FAMILIES, ensure_ascii=False)
    subfamilies_js = json.dumps(SUBFAMILIES, ensure_ascii=False)
    products_js = json.dumps(products, ensure_ascii=False)

    if "const EMBEDDED_FRAGRANCES =" in content:
        content = re.sub(r"const EMBEDDED_FRAGRANCES = .*?;\n", f"const EMBEDDED_FRAGRANCES = {products_js};\n", content, count=1)
        content = re.sub(r"const EMBEDDED_FAMILIES = .*?;\n", f"const EMBEDDED_FAMILIES = {families_js};\n", content, count=1)
        content = re.sub(r"const EMBEDDED_SUBFAMILIES = .*?;\n", f"const EMBEDDED_SUBFAMILIES = {subfamilies_js};\n", content, count=1)
        content_updated = content
    else:
        # Initial insertion if not present yet
        target_start = "<script>"
        replacement = f"""<script>
    // Вбудовані дані каталогу для автономного тестування (GitHub Pages / Standalone)
    const EMBEDDED_FAMILIES = {families_js};
    const EMBEDDED_SUBFAMILIES = {subfamilies_js};
    const EMBEDDED_FRAGRANCES = {products_js};

    let subfamilies = EMBEDDED_SUBFAMILIES;
    let families = EMBEDDED_FAMILIES;
    let allFragrances = EMBEDDED_FRAGRANCES;
    let isServerMode = false;
    let currentSelectedId = 'floral_pure';
    let currentRecommendations = {{ exact: [], adjacent: [], complementary: [] }};

    const SUBFAMILIES_BY_ID = {{}};
    subfamilies.forEach(sf => {{ SUBFAMILIES_BY_ID[sf.id] = sf; }});

    function calculateRingDistance(idxA, idxB) {{
      const diff = Math.abs(idxA - idxB);
      return Math.min(diff, 14 - diff);
    }}

    function classifyRelationship(distance) {{
      if (distance === 0) return 'exact';
      if (distance <= 3) return 'adjacent';
      if (distance >= 5) return 'complementary';
      return 'moderate';
    }}

    function clientSideMatching(sourceSubfamilyId, referenceFragranceId) {{
      let sourceNotes = [];
      if (referenceFragranceId) {{
        const ref = allFragrances.find(f => f.id === referenceFragranceId);
        if (ref) {{
          sourceSubfamilyId = ref.primary_subfamily_id;
          sourceNotes = [...(ref.top_notes || []), ...(ref.heart_notes || []), ...(ref.base_notes || [])];
        }}
      }}

      const srcSf = SUBFAMILIES_BY_ID[sourceSubfamilyId];
      if (!srcSf) return {{ exact: [], adjacent: [], complementary: [] }};

      const buckets = {{ exact: [], adjacent: [], complementary: [] }};

      allFragrances.forEach(f => {{
        if (referenceFragranceId && f.id === referenceFragranceId) return;
        const tgtSf = SUBFAMILIES_BY_ID[f.primary_subfamily_id];
        if (!tgtSf) return;

        const dist = calculateRingDistance(srcSf.ring_index, tgtSf.ring_index);
        const rel = classifyRelationship(dist);

        const targetNotes = [...(f.top_notes || []), ...(f.heart_notes || []), ...(f.base_notes || [])];
        let noteSim = 0;
        if (sourceNotes.length && targetNotes.length) {{
          const sA = new Set(sourceNotes.map(n => n.toLowerCase()));
          const sB = new Set(targetNotes.map(n => n.toLowerCase()));
          let inter = 0;
          sA.forEach(n => {{ if (sB.has(n)) inter++; }});
          noteSim = inter / Math.max(1, (sA.size + sB.size - inter));
        }}

        let score = 0.5;
        if (rel === 'exact') {{
          score = 0.65 + (0.35 * noteSim);
        }} else if (rel === 'adjacent') {{
          const bonus = (dist === 1) ? 0.20 : (dist === 2 ? 0.12 : 0.05);
          score = 0.55 + bonus + (0.25 * noteSim);
        }} else if (rel === 'complementary') {{
          const contrast = (dist === 7) ? 1.0 : 0.88;
          score = 0.50 + (0.30 * contrast) + (0.20 * (1 - noteSim));
        }}

        const item = {{
          fragrance: f,
          relation: rel,
          ring_distance: dist,
          score: Math.round(score * 10000) / 10000,
          target_subfamily: tgtSf
        }};

        if (buckets[rel]) {{
          buckets[rel].push(item);
        }}
      }});

      for (const k in buckets) {{
        buckets[k].sort((a, b) => b.score - a.score);
        buckets[k] = buckets[k].slice(0, 8);
      }}

      return buckets;
    }}"""

        content_updated = content.replace(target_start, replacement, 1)

    # Зберігаємо
    src_html.write_text(content_updated, encoding="utf-8")
    (BASE_DIR / "docs").mkdir(exist_ok=True)
    (BASE_DIR / "docs" / "index.html").write_text(content_updated, encoding="utf-8")
    (BASE_DIR / "index.html").write_text(content_updated, encoding="utf-8")
    print("Standalone & Dual-mode index.html successfully built for GitHub Pages!")

if __name__ == "__main__":
    run_build()
