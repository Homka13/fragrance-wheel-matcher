"""
test_api.py
Інтеграційні тести REST API для Fragrance Wheel Matcher через ASGI TestClient.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from starlette.testclient import TestClient
from fragrance_matcher.app.main import app

def test_api_endpoints():
    client = TestClient(app)

    # 1. Головна сторінка UI
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "Fragrance Wheel Matcher" in res_root.text

    # 2. Отримання структури Колеса (14 підгруп)
    res_wheel = client.get("/api/wheel")
    assert res_wheel.status_code == 200
    wheel_data = res_wheel.json()
    assert len(wheel_data["subfamilies"]) == 14
    assert len(wheel_data["families"]) == 4

    # 3. Наповнення та отримання каталогу парфумів
    client.post("/api/seed")
    res_frags = client.get("/api/fragrances")
    assert res_frags.status_code == 200
    frag_data = res_frags.json()
    assert frag_data["count"] > 0

    # 4. Підбір за підгрупою (oriental_pure)
    res_match_sf = client.post("/api/match", json={"subfamily_id": "oriental_pure"})
    assert res_match_sf.status_code == 200
    match_data = res_match_sf.json()
    recs = match_data["recommendations"]
    assert len(recs["exact"]) > 0
    assert len(recs["adjacent"]) > 0
    assert len(recs["complementary"]) > 0

    # 5. Підбір за референсним парфумом (Carolina Herrera Good Girl)
    res_match_ref = client.post("/api/match", json={"reference_fragrance_id": "carolina_herrera_good_girl"})
    assert res_match_ref.status_code == 200
    ref_recs = res_match_ref.json()["recommendations"]
    assert len(ref_recs["exact"]) > 0

    print("ALL API ENDPOINT TESTS PASSED!")

if __name__ == "__main__":
    test_api_endpoints()
