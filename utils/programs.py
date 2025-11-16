import json
import os

def load_programs():
    path = os.path.join(os.path.dirname(__file__), "../programs.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

programs = load_programs()

muscle_to_exercises = {
    "Бицепс": ["Молотки"],
    "Спина": ["Подтягивания"],
    "Ноги": ["Приседания"],
    "Плечи": ["Махи в стороны"],
    "Пресс": ["Планка"],
    "Низ тела": ["Приседания"],
    "Грудь": ["Отжимания"],
    "Трицепс": ["Отжимания на брусьях"],
    "Предплечья": ["Вис на турнике"]
}