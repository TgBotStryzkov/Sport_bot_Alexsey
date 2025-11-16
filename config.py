import os
from pathlib import Path
from dotenv import load_dotenv

# загрузить переменные из .env
load_dotenv()

# токен читаем из окружения
TOKEN: str = os.getenv("BOT_TOKEN", "")

# ADMIN_ID всегда храним как строку
ADMIN_ID: str = os.getenv("ADMIN_ID", "").strip()

# путь к programs.json (лежит в корне рядом с config.py)
BASE_DIR = Path(__file__).resolve().parent
programs_path = str(BASE_DIR / "programs.json")

# Абсолютный путь к файлу programs.json
programs_path = os.path.join(os.path.dirname(__file__), "programs.json")