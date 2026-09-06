import sys
from pathlib import Path

# Додаємо корінь проекту до sys.path для імпортів у Vercel Serverless Function
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app
