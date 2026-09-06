"""
build_standalone.py
Вбудовує повні дані каталогу Brocard та клієнтський рушій метчингу в index.html,
завдяки чому додаток працює як з бекендом FastAPI/Starlette, так і на GitHub Pages.
"""

import json
from pathlib import Path
from core.wheel_topology import FAMILIES, SUBFAMILIES

BASE_DIR = Path(__file__).resolve().parent

def run_build():
    json_path = BASE_DIR / "data" / "embedded_products.json"
    with open(json_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    src_html = BASE_DIR / "app" / "static" / "index.html"
    content = src_html.read_text(encoding="utf-8")

    # Створюємо вбудовані JSON рядки
    families_js = json.dumps(FAMILIES, ensure_ascii=False)
    subfamilies_js = json.dumps(SUBFAMILIES, ensure_ascii=False)
    products_js = json.dumps(products, ensure_ascii=False)

    # Замінюємо початкову частину тегу <script>
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

    # Також коригуємо initApp та fetchRecommendations
    old_init = """    async function initApp() {
      try {
        const [wheelRes, fragRes] = await Promise.all([
          fetch('/api/wheel'),
          fetch('/api/fragrances')
        ]);
        const wheelData = await wheelRes.json();
        const fragData = await fragRes.json();

        subfamilies = wheelData.subfamilies;
        families = wheelData.families;
        allFragrances = fragData.fragrances || [];

        document.getElementById('catalogCount').innerText = allFragrances.length;

        populatePerfumeSelect();
        renderSvgWheel();
        selectSubfamily('floral_pure');
      } catch (err) {
        console.error('Помилка ініціалізації:', err);
      }
    }"""

    new_init = """    async function initApp() {
      try {
        const testRes = await fetch('/api/wheel');
        if (testRes.ok) {
          isServerMode = true;
          const [wheelData, fragData] = await Promise.all([
            testRes.json(),
            fetch('/api/fragrances').then(r => r.json())
          ]);
          subfamilies = wheelData.subfamilies;
          families = wheelData.families;
          allFragrances = fragData.fragrances || [];
        } else {
          throw new Error('API unavailable');
        }
      } catch (err) {
        isServerMode = false;
        subfamilies = EMBEDDED_SUBFAMILIES;
        families = EMBEDDED_FAMILIES;
        allFragrances = EMBEDDED_FRAGRANCES;
      }

      document.getElementById('catalogCount').innerText = allFragrances.length;
      populatePerfumeSelect();
      renderSvgWheel();
      selectSubfamily('floral_pure');
    }"""

    old_fetch_rec = """    async function fetchRecommendations(subfamilyId, referenceId) {
      try {
        const body = {
          subfamily_id: subfamilyId,
          reference_fragrance_id: referenceId
        };
        const res = await fetch('/api/match', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        const data = await res.json();
        currentRecommendations = data.recommendations || { exact: [], adjacent: [], complementary: [] };
        renderRecommendations();
      } catch (err) {
        console.error('Помилка отримання рекомендацій:', err);
      }
    }"""

    new_fetch_rec = """    async function fetchRecommendations(subfamilyId, referenceId) {
      if (isServerMode) {
        try {
          const body = {
            subfamily_id: subfamilyId,
            reference_fragrance_id: referenceId
          };
          const res = await fetch('/api/match', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
          });
          const data = await res.json();
          currentRecommendations = data.recommendations || { exact: [], adjacent: [], complementary: [] };
        } catch (err) {
          currentRecommendations = clientSideMatching(subfamilyId, referenceId);
        }
      } else {
        currentRecommendations = clientSideMatching(subfamilyId, referenceId);
      }
      renderRecommendations();
    }"""

    # Виконуємо заміни
    content_updated = content.replace(target_start, replacement, 1)
    content_updated = content_updated.replace(old_init, new_init, 1)
    content_updated = content_updated.replace(old_fetch_rec, new_fetch_rec, 1)

    # Зберігаємо
    src_html.write_text(content_updated, encoding="utf-8")
    (BASE_DIR / "docs").mkdir(exist_ok=True)
    (BASE_DIR / "docs" / "index.html").write_text(content_updated, encoding="utf-8")
    (BASE_DIR / "index.html").write_text(content_updated, encoding="utf-8")
    print("Standalone & Dual-mode index.html successfully built for GitHub Pages!")

if __name__ == "__main__":
    run_build()
