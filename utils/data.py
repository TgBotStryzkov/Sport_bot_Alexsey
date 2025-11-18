import os
import json
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from utils.programs import muscle_to_exercises
from typing import Optional, Tuple
import logging


# Получает путь к файлу пользователя по его ID
def get_user_file(user_id: int) -> str:
    return os.path.join(USERS_DIR, f"{user_id}.json")

# 📁 Путь к папке с пользователями
USERS_DIR = "users"

def load_user_data(user_id):
    path = get_user_file(user_id)
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logging.warning("Файл пользователя %s повреждён (JSONDecodeError): %s", user_id, e)
        # опционально: можно сделать резервную копию
        # os.rename(path, path + ".broken")
        return {}
    except Exception as e:
        logging.exception("Не удалось прочитать файл пользователя %s: %s", user_id, e)
        return {}


def write_user_data(user_id, data):
    os.makedirs(USERS_DIR, exist_ok=True)
    path = get_user_file(user_id)

    if "username" not in data:
        data["username"] = "неизвестно"

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.exception("Не удалось записать данные пользователя %s: %s", user_id, e)


def get_all_user_ids() -> list[str]:
    """Возвращает список всех user_id, у которых есть json-файлы"""
    if not os.path.exists(USERS_DIR):
        return []
    return [
        filename.replace(".json", "")
        for filename in os.listdir(USERS_DIR)
        if filename.endswith(".json")
    ]

def ensure_user_file_exists(user_id: str, username: str):
    os.makedirs(USERS_DIR, exist_ok=True)
    path = get_user_file(user_id)
    if not os.path.exists(path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"username": username}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.exception("Не удалось создать файл пользователя %s: %s", user_id, e)


# Разбирает ввод вида 3x10x20 на три числа
def разобрать_результат(s: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    try:
        s = s.lower().strip().replace("х", "x").replace("×", "x").replace("*", "x")
        parts = [p.strip() for p in s.split("x") if p.strip()]
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            return None, None, None
        a, b, c = map(int, parts)
        return a, b, c
    except (ValueError, AttributeError):
        return None, None, None



# ─── Функция для прогресс-бара ─── #
def get_progress_bar(percent):
    blocks = int(percent / 10)
    return "▓" * blocks + "░" * max(0, 10 - blocks)


def get_today_trained_muscles(user_id: str) -> list[str]:
    data = load_user_data(user_id)
    today = datetime.now().strftime("%Y-%m-%d")

    # упражнения, которые пользователь сегодня зафиксировал
    today_exercises = [
        e.lower().strip()
        for e in data.get(today, {}).get("тренировка", {}).keys()
    ]

    muscles_done: list[str] = []

    for muscle, default_ex in muscle_to_exercises.items():
        # пользовательские изменения по этой группе
        custom = data.get("доп_упражнения", {}).get(muscle, [])
        removed = data.get("удалённые_системные", {}).get(muscle, [])

        # актуальный список упражнений группы = (системные − удалённые) + добавленные
        all_ex = [e for e in default_ex if e not in removed] + list(custom)

        # нормализуем для сравнения
        all_ex_norm = [e.lower().strip() for e in all_ex if e]

        # группа «закрыта», если все актуальные упражнения присутствуют сегодня
        if all_ex_norm and all(e in today_exercises for e in all_ex_norm):
            muscles_done.append(muscle)

    return muscles_done

# Сохраняет данные пользователя из сообщения
async def save_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        logging.error("save_user_data вызван без update.message")
        return

    try:
        user_id = str(update.message.from_user.id)
        username = update.message.from_user.username or "неизвестно"
        text = update.message.text
        today = datetime.now().strftime("%Y-%m-%d")

        data = load_user_data(user_id)
        data["username"] = username  # имя обновляем в памяти


    
        # 1) разобрать строки "ключ: значение"
        lines = [l for l in (text or "").splitlines() if l.strip()]
        pairs = [(k.strip(), v.strip()) for l in lines if ":" in l for k, v in [l.split(":", 1)]]

        # 🔹 если нет ни одной строки вида "ключ: значение" — вообще ничего не сохраняем
        if not pairs:
            return

        # 2) эвристика: это тренировка, если ВСЕ пары похожи на упражнения
        exercise_keywords = ("присед", "жим", "тяга", "подтяг", "отжим", "планка")
        is_workout = bool(pairs) and all(any(w in k.lower() for w in exercise_keywords) for k, _ in pairs)

        if is_workout:
            day = data.setdefault(today, {})
            day["тренировка"] = {k: v for k, v in pairs}
            write_user_data(user_id, data)

            if update.message:
                msg = [f"📋 Тренировка за {today}:\n"]
                msg += [f"{name.capitalize()}: {reps}" for name, reps in day["тренировка"].items()]
                await update.message.reply_text("\n".join(msg))
            return

        # 3) обычный ввод: сначала entry...
        entry = {k: v for k, v in pairs}

        # 4) потом выделяем упражнения внутри entry["упражнения"]
        exercises = {k: v for k, v in entry.items() if any(w in k.lower() for w in exercise_keywords)}
        if exercises:
            entry["упражнения"] = exercises

        # 5) сохранить
        day = data.setdefault(today, {})
        day.update(entry)
        write_user_data(user_id, data)

        if update.message:
            await update.message.reply_text("✅ Данные сохранены! Напиши /card, чтобы посмотреть.")
            
    except Exception as e:
        logging.exception("Ошибка в save_user_data: %s", e)
        if update.message:
            try:
                await update.message.reply_text(
                    "⚠️ Не удалось сохранить данные. Попробуй ещё раз."
                )
            except Exception:
                # если даже ответить не получилось — просто замолкаем
                pass