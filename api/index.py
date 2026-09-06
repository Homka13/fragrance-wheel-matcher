import sys
import json
from pathlib import Path

# Додаємо корінь проекту до sys.path для імпортів у Vercel Serverless Function
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

app = None

try:
    from app.main import app as main_app
    app = main_app
except Exception as e:
    print(f"Fallback to standalone API in api/index.py due to: {e}")

if app is None:
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    DATA_FILE = Path(__file__).resolve().parent / "embedded_products.json"
    if not DATA_FILE.exists():
        DATA_FILE = PROJECT_ROOT / "data" / "embedded_products.json"

    try:
        from core.wheel_topology import FAMILIES, SUBFAMILIES
        from core.matcher import find_recommendations
    except ImportError:
        try:
            from ..core.wheel_topology import FAMILIES, SUBFAMILIES
            from ..core.matcher import find_recommendations
        except Exception:
            FAMILIES = {}
            SUBFAMILIES = []
            find_recommendations = None

    def get_products():
        if DATA_FILE.exists():
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    async def get_wheel(request):
        return JSONResponse({"families": FAMILIES, "subfamilies": SUBFAMILIES})

    async def get_frags(request):
        products = get_products()
        return JSONResponse({"fragrances": products, "count": len(products)})

    async def match_frags(request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        subfamily_id = body.get("subfamily_id", "floral_pure")
        ref_id = body.get("reference_fragrance_id")
        products = get_products()
        if find_recommendations:
            res = find_recommendations(all_fragrances=products, source_subfamily_id=subfamily_id, reference_fragrance_id=ref_id)
        else:
            res = {"exact": [], "adjacent": [], "complementary": []}
        return JSONResponse({"status": "success", "recommendations": res})

    routes = [
        Route("/api/wheel", get_wheel, methods=["GET"]),
        Route("/api/fragrances", get_frags, methods=["GET"]),
        Route("/api/match", match_frags, methods=["POST"]),
        Route("/wheel", get_wheel, methods=["GET"]),
        Route("/fragrances", get_frags, methods=["GET"]),
        Route("/match", match_frags, methods=["POST"]),
    ]
    app = Starlette(routes=routes)

