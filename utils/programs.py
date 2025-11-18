import json
import os
import logging

def load_programs():
    """Безопасно загружает programs.json. При ошибке возвращает {}."""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "programs.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning("Файл programs.json не найден, используем пустой словарь программ.")
        return {}
    except json.JSONDecodeError as e:
        logging.warning("Файл programs.json повреждён (JSONDecodeError): %s", e)
        return {}
    except Exception as e:
        logging.exception("Не удалось загрузить programs.json: %s", e)
        return {}


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