"""
main.py
Веб-додаток та API для Fragrance Wheel Matcher на базі Starlette + Uvicorn.
Забезпечує ендпоінти для отримання геометрії Колеса, каталогу парфумів та інтерактивного підбору.
"""

import json
from pathlib import Path
from typing import Optional

from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse, FileResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

try:
    from core.wheel_topology import FAMILIES, SUBFAMILIES, SUBFAMILIES_BY_ID
    from core.matcher import find_recommendations
    from db.database import get_db, init_db
    from db.models import FragranceModel, BrandModel
    from pipeline.ingest import ingest_from_file
except ImportError:
    try:
        from ..core.wheel_topology import FAMILIES, SUBFAMILIES, SUBFAMILIES_BY_ID
        from ..core.matcher import find_recommendations
        from ..db.database import get_db, init_db
        from ..db.models import FragranceModel, BrandModel
        from ..pipeline.ingest import ingest_from_file
    except ImportError:
        from fragrance_matcher.core.wheel_topology import FAMILIES, SUBFAMILIES, SUBFAMILIES_BY_ID
        from fragrance_matcher.core.matcher import find_recommendations
        from fragrance_matcher.db.database import get_db, init_db
        from fragrance_matcher.db.models import FragranceModel, BrandModel
        from fragrance_matcher.pipeline.ingest import ingest_from_file

STATIC_DIR = Path(__file__).resolve().parent / "static"
SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed_catalog.json"


def ensure_db_ready():
    """Забезпечує готовність БД та завантаження каталогу навіть у Serverless (Vercel/Lambda)."""
    try:
        init_db()
        with get_db() as session:
            count = session.query(FragranceModel).count()
            if count == 0 and SEED_FILE.exists():
                ingest_from_file(str(SEED_FILE))
    except Exception as e:
        print(f"Warning in ensure_db_ready: {e}")


try:
    ensure_db_ready()
except Exception:
    pass


async def get_wheel_data(request):
    """Повертає структуру сімейств та 14 підгруп Колеса Едвардса."""
    return JSONResponse({
        "families": FAMILIES,
        "subfamilies": SUBFAMILIES
    })


async def get_all_fragrances(request):
    """Повертає каталог парфумів із бази даних або fallback з файлу seed_catalog.json."""
    data = []
    try:
        ensure_db_ready()
        with get_db() as session:
            frags = session.query(FragranceModel).all()
            data = [f.to_dict() for f in frags]
    except Exception as e:
        print(f"DB query error: {e}")

    # Fallback, якщо в serverless базі порожньо
    if not data and SEED_FILE.exists():
        try:
            with open(SEED_FILE, "r", encoding="utf-8") as f:
                seed = json.load(f)
                data = seed.get("products", [])
        except Exception as e:
            print(f"Fallback read error: {e}")

    return JSONResponse({"fragrances": data, "count": len(data)})


async def match_fragrances(request):
    """
    Головний ендпоінт підбору:
    Приймає JSON:
    - subfamily_id (опціонально)
    - reference_fragrance_id (опціонально)
    - preferred_notes (опціонально)
    - disliked_notes (опціонально)
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    subfamily_id = body.get("subfamily_id")
    reference_id = body.get("reference_fragrance_id")
    preferred_notes = body.get("preferred_notes", [])
    disliked_notes = body.get("disliked_notes", [])

    all_frags = []
    try:
        ensure_db_ready()
        with get_db() as session:
            frags = session.query(FragranceModel).all()
            all_frags = [f.to_dict() for f in frags]
    except Exception as e:
        print(f"DB match error: {e}")

    # Якщо база порожня, автоматично завантажуємо стартовий каталог
    if not all_frags and SEED_FILE.exists():
        try:
            ingest_from_file(str(SEED_FILE))
            with get_db() as session:
                frags = session.query(FragranceModel).all()
                all_frags = [f.to_dict() for f in frags]
        except Exception:
            pass

        if not all_frags:
            try:
                with open(SEED_FILE, "r", encoding="utf-8") as f:
                    seed = json.load(f)
                    all_frags = seed.get("products", [])
            except Exception:
                pass

    if not subfamily_id and not reference_id:
        # За замовчуванням беремо першу квіткову групу
        subfamily_id = "floral_pure"

    try:
        results = find_recommendations(
            all_fragrances=all_frags,
            source_subfamily_id=subfamily_id,
            reference_fragrance_id=reference_id,
            preferred_notes=preferred_notes,
            disliked_notes=disliked_notes,
            limit_per_category=8
        )
        return JSONResponse({
            "status": "success",
            "source_subfamily_id": subfamily_id,
            "reference_fragrance_id": reference_id,
            "recommendations": results
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)


async def seed_database(request):
    """Перезавантажує каталог бестселерів парфумерії у БД."""
    if not SEED_FILE.exists():
        return JSONResponse({"status": "error", "message": "Файл seed каталогу не знайдено"}, status_code=404)

    res = ingest_from_file(str(SEED_FILE))
    return JSONResponse({"status": "success", "summary": res})


async def serve_index(request):
    """Головна HTML сторінка додатку."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>Fragrance Wheel Matcher</h1><p>index.html not found</p>")


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app):
    init_db()
    with get_db() as session:
        count = session.query(FragranceModel).count()
        if count == 0 and SEED_FILE.exists():
            print("База порожня. Автоматичний імпорт seed_catalog.json...")
            ingest_from_file(str(SEED_FILE))
    yield


# Маршрутизація
routes = [
    Route("/", serve_index, methods=["GET"]),
    Route("/api/wheel", get_wheel_data, methods=["GET"]),
    Route("/api/fragrances", get_all_fragrances, methods=["GET"]),
    Route("/api/match", match_fragrances, methods=["POST"]),
    Route("/api/seed", seed_database, methods=["POST"]),
]

app = Starlette(routes=routes, lifespan=lifespan)
