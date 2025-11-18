import logging
from datetime import datetime

from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from utils.data import load_user_data, get_today_trained_muscles




def get_main_menu():
    keyboard = [
        [KeyboardButton("📝 Добавить данные за сегодня"), KeyboardButton("📊 Показать карту")],
        [KeyboardButton("📈 График веса"), KeyboardButton("📋 Карта тренировки")],
        [KeyboardButton("📈 Моя статистика"), KeyboardButton("🏁 Начать тренировку")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


def get_edit_card_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🏋️‍♂️ Вес", callback_data="edit_field:weight"),
            InlineKeyboardButton("👟 Шаги", callback_data="edit_field:steps")
        ],
        [
            InlineKeyboardButton("😴 Сон", callback_data="edit_field:sleep"),
            InlineKeyboardButton("🔥 Калории", callback_data="edit_field:calories")
        ],
        [
            InlineKeyboardButton("🎯 Цели", callback_data="edit_goals") 
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_program_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("Фулбади", callback_data="программа_фулбади"),
            InlineKeyboardButton("Сплит", callback_data="программа_сплит")
        ],
        [
            InlineKeyboardButton("Верх/Низ", callback_data="программа_верх/низ")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_exercise_card_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Изменить карточку", callback_data="edit_card_fields")]
    ])


def get_muscle_keyboard(мышцы: list[str]):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(м, callback_data=f"мышца_{м}")] for м in мышцы
    ])

def кнопки_мышц_фулбади(user_id):
    muscles = ["Грудь", "Спина", "Ноги", "Бицепс", "Трицепс", "Плечи", "Пресс", "Предплечья"]
    trained = set()

    try:
        trained_list = get_today_trained_muscles(user_id) or []
        trained = set(trained_list)
    except Exception as e:
        logging.exception("Ошибка при получении тренированных мышц для %s: %s", user_id, e)

    keyboard = []
    row = []
    for i, muscle in enumerate(muscles):
        label = f"{muscle} ✅" if muscle in trained else muscle
        # важное изменение: без .lower(), чтобы совпадало с остальной логикой
        row.append(InlineKeyboardButton(label, callback_data=f"мышца_{muscle}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)



def get_exercise_options_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить упражнение", callback_data="добавить_упражнение")],
        [InlineKeyboardButton("🗑 Удалить упражнение", callback_data="удалить_упражнение")],
        [InlineKeyboardButton("🔙 Назад", callback_data="назад_к_мышцам")]
    ])

def get_full_exercise_keyboard(exercises: list[str], user_id: str = None):
    buttons = []
    row = []

    выполненные = set()
    if user_id:
        try:
            data = load_user_data(user_id)
            today = datetime.now().strftime("%Y-%m-%d")
            выполненные = set(data.get(today, {}).get("тренировка", {}).keys())
        except Exception as e:
            logging.exception("Ошибка при получении выполненных упражнений для %s: %s", user_id, e)


    for i, ex in enumerate(exercises):
        галочка = " ✅" if ex in выполненные else ""
        row.append(InlineKeyboardButton(ex + галочка, callback_data=f"упр_{ex}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # Стандартные нижние кнопки
    buttons += [
        [InlineKeyboardButton("➕ Добавить упражнение", callback_data="добавить_упражнение")],
        [InlineKeyboardButton("🗑 Удалить упражнение", callback_data="удалить_упражнение")],
        [InlineKeyboardButton("🔙 Назад", callback_data="назад_к_мышцам")]
    ]

    return InlineKeyboardMarkup(buttons)