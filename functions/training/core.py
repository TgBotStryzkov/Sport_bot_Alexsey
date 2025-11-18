from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime
from utils.data import load_user_data, write_user_data, разобрать_результат
from utils.keyboard import (
    get_program_keyboard,
    get_muscle_keyboard,
    get_exercise_options_keyboard
)
import os
import json
from utils.data import get_today_trained_muscles
import logging



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
programs_path = os.path.join(BASE_DIR, "..", "..", "programs.json")

try:
    with open(programs_path, "r", encoding="utf-8") as f:
        programs = json.load(f)
except Exception as e:
    logging.exception("Не удалось загрузить programs.json: %s", e)
    programs = {}




# Обработка нажатия на "Фулбади", "Сплит" и т.п.
async def choose_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        logging.error("choose_program вызван без callback_query")
        return

    try:
        await query.answer()
        выбор = (query.data or "").replace("программа_", "")
        context.user_data["выбранная_программа"] = выбор

        print("[DEBUG] Пользователь выбрал программу:", выбор)

        мышцы = programs.get(выбор, [])
        if мышцы:
            await query.edit_message_text(
                text="Теперь выбери мышцу:",
                reply_markup=get_muscle_keyboard(мышцы)
            )
        else:
            await query.edit_message_text("❌ Не удалось загрузить мышцы для этой программы.")
    except Exception as e:
        logging.exception("Ошибка в choose_program: %s", e)
        try:
            await query.message.reply_text("⚠️ Не удалось выбрать программу, попробуй ещё раз.")
        except Exception:
            pass


# Обрабатывает введение нового упражнения
async def показать_следующее_упражнение(update, context):
    try:
        тренировка = context.user_data.get("текущая_тренировка", {})
        оставшиеся = тренировка.get("упражнения", [])

        if not оставшиеся:
            # Сохраняем программу перед очисткой
            программа = context.user_data.get("выбранная_программа")
            context.user_data.clear()
            if программа:
                context.user_data["выбранная_программа"] = программа

            callback_func = program_callbacks.get(программа, назад_к_мышцам_callback)
            await callback_func(update, context)
            return

        текущее = оставшиеся[0]
        context.user_data["текущее_упражнение"] = текущее
        context.user_data["state"] = "exercise_result"

        # Определяем, куда отправлять сообщение
        target_message = None
        if getattr(update, "message", None):
            target_message = update.message
        elif getattr(update, "callback_query", None) and update.callback_query.message:
            target_message = update.callback_query.message

        if target_message:
            await target_message.reply_text(
                f"🔸 {текущее}\n\n"
                f"Введи результат в формате: `3x10x20` (подходы x повторы x вес)",
                parse_mode="Markdown"
            )
        else:
            logging.error("показать_следующее_упражнение: нет message или callback_query.message")
    except Exception as e:
        logging.exception("Ошибка в показать_следующее_упражнение: %s", e)


# ─── Показ упражнений по выбранной мышце ───
async def choose_muscle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        logging.error("choose_muscle вызван без callback_query")
        return

    try:
        await query.answer()
        мышца = (query.data or "").replace("мышца_", "")
        context.user_data["выбранная_мышца"] = мышца

        user_id = str(query.from_user.id)
        data = load_user_data(user_id)
        
        упражнения = {
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

        список = упражнения.get(мышца, []).copy()  # системные упражнения

        # Исключаем удалённые системные упражнения
        удалённые = data.get("удалённые_системные", {}).get(мышца, [])
        список = [упр for упр in список if упр not in удалённые]

        доп = data.get("доп_упражнения", {}).get(мышца, [])
        список += доп

        context.user_data["список_упражнений"] = список
        from utils.keyboard import get_full_exercise_keyboard

        context.user_data["state"] = "count_input"
        reply_markup = get_full_exercise_keyboard(список, user_id=user_id)

        await query.edit_message_text(
            f"📌 Упражнения на {мышца}. Используй кнопки ниже:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logging.exception("Ошибка в choose_muscle: %s", e)
        try:
            await query.message.reply_text("⚠️ Не удалось загрузить упражнения. Попробуй ещё раз.")
        except Exception:
            pass






# ─── Команда /начать_упражнения ─── #
async def начать_упражнения_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    мышца = context.user_data.get("выбранная_мышца", "мышца")
    упражнения = context.user_data.get("список_упражнений", [])

    if not упражнения:
        await query.edit_message_text("❌ Упражнения не найдены.")
        return

    текст = f"🏁 Начинаем тренировку на {мышца}!\n\n"
    for упр in упражнения:
        текст += f"🔸 {упр}\n"

    текст += "\nКогда завершишь, отправь свой отчёт\n"

    await query.edit_message_text(текст)

    # ✅ Сохраняем выбранную программу до очистки
    выбранная_программа = context.user_data.get("выбранная_программа", "неизвестно").strip().lower()

    context.user_data.clear()

    # ✅ Используем сохранённую переменную
    print("[DEBUG] выбранная_программа перед сохранением тренировки:", выбранная_программа)

    context.user_data["выбранная_программа"] = выбранная_программа  # восстановим
    context.user_data["текущая_тренировка"] = {
        "мышца": мышца,
        "упражнения": упражнения.copy(),
        "индекс": 0,
        "программа": выбранная_программа,
        "прогресс": {}
    }

    # Показываем первое упражнение
    await показать_следующее_упражнение(update, context)




async def назад_к_мышцам_callback_сплит(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        программа = context.user_data.get("выбранная_программа")
        стандартные_мышцы = ["Грудь", "Трицепс", "Спина", "Бицепс", "Ноги", "Плечи"]
        мышцы = programs.get(программа, стандартные_мышцы) if программа else стандартные_мышцы

        if not мышцы:
            все_мышцы = set()
            for prog in programs.values():
                все_мышцы.update(prog)
            мышцы = sorted(все_мышцы)

        # ✅ Получаем проработанные мышцы на сегодня
        user_id = str(update.effective_user.id)
        тренированные = get_today_trained_muscles(user_id)

        # 🧩 Собираем клавиатуру с галочками
        keyboard = [
            [InlineKeyboardButton(f"{м} ✅" if м in тренированные else м,
                                callback_data=f"мышца_{м}")]
            for м in мышцы
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Кнопка или обычное сообщение
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.message.edit_text("Теперь выбери мышцу:", reply_markup=reply_markup)
        elif update.message:
            await update.message.reply_text("Теперь выбери мышцу:", reply_markup=reply_markup)

    except Exception as e:
        logging.exception("Ошибка в назад_к_мышцам_callback_сплит: %s", e)



async def назад_к_мышцам_callback_присылает_новое_смс(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        программа = context.user_data.get("выбранная_программа")
        стандартные_мышцы = ["Грудь", "Спина", "Ноги", "Бицепс", "Трицепс", "Плечи", "Пресс", "Предплечья"]

        мышцы = programs.get(программа, стандартные_мышцы) if программа else стандартные_мышцы

        if not мышцы:
            все_мышцы = set()
            for prog in programs.values():
                все_мышцы.update(prog)
            мышцы = sorted(все_мышцы)

        keyboard = [[InlineKeyboardButton(м, callback_data=f"мышца_{м}")] for м in мышцы]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Всегда отправляем новое сообщение, а не редактируем старое
        chat_id = update.effective_chat.id
        await context.bot.send_message(
            chat_id=chat_id,
            text="Теперь выбери мышцу:",
            reply_markup=reply_markup
        )

    except Exception as e:
        logging.exception("Ошибка в назад_к_мышцам_callback_присылает_новое_смс: %s", e)





async def назад_к_мышцам_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        программа = context.user_data.get("выбранная_программа", "").strip().lower()

        muscles_by_program = {
            "сплит": ["Грудь", "Трицепс", "Спина", "Бицепс", "Ноги", "Плечи"],
            "фулбади": ["Грудь", "Спина", "Ноги", "Бицепс", "Трицепс", "Плечи", "Пресс", "Предплечья"],
            "верх/низ": ["Верх", "Низ"],
        }

        мышцы = muscles_by_program.get(программа, muscles_by_program["фулбади"])

        # ✅ Получаем проработанные мышцы на сегодня
        user_id = str(update.effective_user.id)
        тренированные = get_today_trained_muscles(user_id)

        # 🧩 Собираем клавиатуру с галочками (если фулбади)
        keyboard = []
        for м in мышцы:
            label = f"{м} ✅" if м in тренированные else м
            keyboard.append([InlineKeyboardButton(label, callback_data=f"мышца_{м}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Показываем сообщение
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.message.edit_text("Теперь выбери мышцу:", reply_markup=reply_markup)
        elif update.message:
            await update.message.reply_text("Теперь выбери мышцу:", reply_markup=reply_markup)

    except Exception as e:
        logging.exception("Ошибка в назад_к_мышцам_callback: %s", e)




# Добавляет новое упражнение в список пользователя
async def добавить_упражнение_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        logging.error("добавить_упражнение_callback вызван без callback_query")
        return
    
    try:
        await query.answer()
        await query.edit_message_text("✍️ Введи название нового упражнения:")
        context.user_data["ожидаем_новое_упражнение"] = True

    except Exception as e:
        logging.exception("Ошибка в добавить_упражнение_callback: %s", e)
        try:
            await query.message.reply_text("⚠️ Не удалось начать добавление упражнения.")
        except Exception:
            pass


# Удаляет упражнение из списка пользователя
async def удалить_упражнение_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        logging.error("удалить_упражнение_callback вызван без callback_query")
        return

    try:
        await query.answer()

        # Получаем выбранную мышцу из пользовательских данных
        muscle = context.user_data.get("выбранная_мышца")
        user_id = str(query.from_user.id)
        data = load_user_data(user_id)

        упражнения = {
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
        
        доп = data.get("доп_упражнения", {}).get(muscle, [])
        системные = упражнения.get(muscle, []).copy()
        удалённые = data.get("удалённые_системные", {}).get(muscle, [])
        системные = [упр for упр in системные if упр not in удалённые]

        user_exercises = доп + системные


        if not user_exercises:
            await query.edit_message_text("❌ У тебя нет добавленных упражнений для этой мышцы.")

            # Повторно показать упражнения
            упражнения = {
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

            список = упражнения.get(muscle, ["Нет заданных упражнений"])
            доп = data.get("доп_упражнения", {}).get(muscle, [])
            список += доп

            context.user_data["список_упражнений"] = список

            текст = f"📌 Упражнения на {muscle}:\n" + "\n".join(f"• {упр}" for упр in список)
        
            await query.message.reply_text(текст, reply_markup=get_exercise_options_keyboard())
            return


        keyboard = [
            [InlineKeyboardButton(f"❌ {упр}", callback_data=f"удали_упр_{i}")]
            for i, упр in enumerate(user_exercises)
        ]
        context.user_data["удаляемые_упражнения"] = user_exercises
        await query.edit_message_text(
            "Выбери упражнение, которое хочешь удалить:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logging.exception("Ошибка в удалить_упражнение_callback: %s", e)
        try:
            await query.message.reply_text("⚠️ Не удалось подготовить список упражнений для удаления.")
        except Exception:
            pass

# Обрабатывает удаление упражнения из списка (системного или дополнительного)
async def обработать_удаление_упражнения(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        logging.error("обработать_удаление_упражнения вызван без callback_query")
        return

    try:
        await query.answer()

        if not query.data.startswith("удали_упр_"):
            return

        index = int(query.data.replace("удали_упр_", ""))
        muscle = context.user_data.get("выбранная_мышца")
        user_id = str(query.from_user.id)
        data = load_user_data(user_id)

        # Список системных упражнений
        упражнения = {
            "Бицепс": ["Молотки"],
            "Спина": ["Подтягивания"],
            "Ноги": ["Приседания"],
            "Плечи": ["Махи в стороны"],
            "Пресс": ["Планка"],
            "Грудь": ["Отжимания"],
            "Трицепс": ["Французский жим"],
            "Низ тела": ["Приседания"]
        }

        системные = упражнения.get(muscle, [])
        удалённые = data.get("удалённые_системные", {}).get(muscle, [])
        системные = [упр for упр in системные if упр not in удалённые]

        доп = data.get("доп_упражнения", {}).get(muscle, [])
        все_упражнения = context.user_data.get("удаляемые_упражнения", [])


        if 0 <= index < len(все_упражнения):
            удалённое = все_упражнения[index]

            if удалённое in доп:
                доп.remove(удалённое)
                data["доп_упражнения"][muscle] = доп
            else:
                data.setdefault("удалённые_системные", {}).setdefault(muscle, []).append(удалённое)

            write_user_data(user_id, data)

            # 1. Изменяем текущее сообщение на подтверждение удаления
            await query.edit_message_text(f"✅ Упражнение «{удалённое}» удалено!")

            # 2. Показываем выбор мышц новым сообщением
            await назад_к_мышцам_callback_присылает_новое_смс(update, context)
        else:
            await query.edit_message_text("❌ Ошибка при удалении.")
    
    except Exception as e:
        logging.exception("Ошибка в обработать_удаление_упражнения: %s", e)
        try:
            await query.message.reply_text("⚠️ Не удалось удалить упражнение. Попробуй ещё раз.")
        except Exception:
            pass



# ─── Начало пользовательской тренировки ───
async def start_custom_workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logging.error("start_custom_workout вызван без update.message")
        return ConversationHandler.END
    
    try:
        context.user_data.clear()
        context.user_data["state"] = "awaiting_program_selection"

        if update.message:
            await update.message.reply_text("Выбери тип тренировки:", reply_markup=get_program_keyboard())
        return ConversationHandler.END  # <== мы уходим из диалога, дальше логика идёт в choose_program
    
    except Exception as e:
        logging.exception("Ошибка в start_custom_workout: %s", e)
        return ConversationHandler.END



# Показываем выбор программ при нажатии "Начать тренировку"
async def handle_exercise_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logging.error("handle_exercise_button вызван без update.message")
        return ConversationHandler.END
    
    try:
        if update.message:
            await update.message.reply_text("Выбери тип тренировки:", reply_markup=get_program_keyboard())

    except Exception as e:
        logging.exception("Ошибка в handle_exercise_button: %s", e)


# ─── Получение количества упражнений и показ мышц ───
async def receive_exercise_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logging.error("receive_exercise_count вызван без update.message")
        return ASK_EXERCISE_COUNT
    
    try:
        count = int(update.message.text.strip())
        context.user_data["упражнений_всего"] = count

        # Пример списка мышц — пока хардкодим
        muscles = ["Бицепс", "Спина", "Ноги", "Плечи", "Пресс"]
        context.user_data["список_мышц"] = muscles
        keyboard = [[InlineKeyboardButton(м, callback_data=f"мышца_{м}")] for м in muscles]
        markup = InlineKeyboardMarkup(keyboard)
        if update.message:
            await update.message.reply_text("Выбери мышцу для начала:", reply_markup=get_muscle_keyboard(muscles))
        return CHOOSE_MUSCLE
    
    except ValueError:
        if update.message:
            await update.message.reply_text("❌ Введи число, например 5.")
        return ASK_EXERCISE_COUNT



program_callbacks = {
    "фулбади": назад_к_мышцам_callback,
    "сплит": назад_к_мышцам_callback_сплит,
    "верх/низ": назад_к_мышцам_callback_сплит
}

мышцы_по_программе = {
    "Фулбади": ["Грудь", "Спина", "Ноги", "Бицепс", "Трицепс", "Плечи", "Пресс", "Предплечья"],
    "Сплит": ["Грудь", "Трицепс", "Спина", "Бицепс", "Ноги", "Плечи"],
    "Верх/Низ": ["Верх тела", "Низ тела"],
}


# ─── Сохранение результата упражнения ─── #
async def сохранить_результат_упражнения(update, context):
    if not update.message:
        logging.error("сохранить_результат_упражнения вызван без update.message")
        return

    try:
        user_id = str(update.message.from_user.id)
        текст = update.message.text.strip()

        упражнение = context.user_data.get("текущее_упражнение")
        тренировка = context.user_data.get("текущая_тренировка")

        if not упражнение or not тренировка:
            await update.message.reply_text("❗ Нет активной тренировки. Начни тренировку заново.")
            context.user_data.pop("текущая_тренировка", None)
            context.user_data.pop("текущее_упражнение", None)
            return

        today = datetime.now().strftime("%Y-%m-%d")

        # Загружаем данные
        data = load_user_data(user_id)

        if today not in data:
            data[today] = {}

        if not isinstance(data[today].get("тренировка"), dict):
            data[today]["тренировка"] = {}

        # Ищем все прошлые результаты этого упражнения
        прошлое = None
        все_результаты = []

        for дата, инфо in data.items():
            if дата in ("цели", "username"):
                continue
            тренировка_данные = инфо.get("тренировка", {})
            if isinstance(тренировка_данные, dict):
                результат = тренировка_данные.get(упражнение)
                if результат:
                    все_результаты.append(результат)

        if все_результаты:
            прошлое = max(
                все_результаты,
                key=lambda txt: разобрать_результат(txt)[2] if разобрать_результат(txt)[2] is not None else 0
            )

        # Сохраняем ввод
        data[today]["тренировка"][упражнение] = текст
        сообщение = f"📌 {упражнение}: {текст}"

        # Сравнение по числам
        тек_поды, тек_повт, тек_вес = разобрать_результат(текст)
        if прошлое:
            прош_поды, прош_повт, прош_вес = разобрать_результат(прошлое)

            # Сравниваем только если и прошлый, и текущий вес известны
            if тек_вес is not None and прош_вес is not None:
                if тек_вес > прош_вес:
                    сообщение += "\n📈 Отлично! Ты поднял больший вес! 💪"
                elif тек_вес == прош_вес and тек_повт is not None and прош_повт is not None and тек_повт > прош_повт:
                    сообщение += "\n⚡ Ты сделал больше повторов при том же весе. Пора увеличить вес! ⬆️"
                elif (тек_вес < прош_вес) or (тек_повт is not None and прош_повт is not None and тек_повт < прош_повт):
                    сообщение += "\n🔻 Меньше, чем раньше. Может, дал себе отдых? Или не тот день?"
                else:
                    сообщение += "\n📊 Повторил прежний результат — стабильность тоже сила!"
            else:
                # Если вес не указан хотя бы в одном из результатов
                сообщение += "\n✅ Результат сохранён! (Вес не сравниваю, так как не хватает данных.)"


        write_user_data(user_id, data)
        await update.message.reply_text(сообщение)

        # Удаляем выполненное упражнение из списка
        if "упражнения" in тренировка and тренировка["упражнения"]:
            тренировка["упражнения"].pop(0)

            # Если остались упражнения - показываем следующее
            if тренировка["упражнения"]:
                следующее_упражнение = тренировка["упражнения"][0]
                context.user_data["текущее_упражнение"] = следующее_упражнение
                await update.message.reply_text(
                    f"🔸 {следующее_упражнение}\n\n"
                    f"Введи результат в формате: `3x10x20` (подходы x повторы x вес)",
                    parse_mode="Markdown"
                )
            else:
                # Получаем название программы из текущей тренировки
                программа = тренировка.get("программа", "Фулбади")

                context.user_data.clear()
                context.user_data["выбранная_программа"] = программа

                # Вызываем соответствующую функцию показа кнопок мышц
                print(f"[DEBUG] программа из тренировки: {программа}")
                callback_func = program_callbacks.get(программа)

                if callback_func:
                    await callback_func(update, context)
                else:
                    await update.message.reply_text("❗ Ошибка: программа не найдена.")
        else:
            await update.message.reply_text("✅ Упражнение сохранено!")
            context.user_data.pop("текущая_тренировка", None)
            context.user_data.pop("текущее_упражнение", None)

    except Exception as e:
        logging.exception("Ошибка в сохранить_результат_упражнения: %s", e)
        try:
            await update.message.reply_text("⚠️ Не удалось сохранить результат. Попробуй ещё раз.")
        except Exception:
            pass



# 🔹 Обработка нажатия на кнопку конкретного упражнения
async def handle_exercise_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        logging.error("handle_exercise_click вызван без callback_query")
        return
    
    try:
        await query.answer()
        название = query.data.replace("упр_", "").strip()
        context.user_data["state"] = "exercise_result"
        context.user_data["текущее_упражнение"] = название

        # Создаём временную тренировку с одним упражнением (если её ещё нет)
        context.user_data.setdefault("текущая_тренировка", {
            "упражнения": [название],
            "мышца": context.user_data.get("выбранная_мышца", ""),
            "программа": context.user_data.get("выбранная_программа", "неизвестно"),
            "прогресс": {}
        })

        await query.message.reply_text(
            f"📛 {название}\nВведи результат в формате: 3x10x20 (подходы x повторы x вес)"
        )

    except Exception as e:
        logging.exception("Ошибка в handle_exercise_click: %s", e)

# Этапы диалога
ASK_EXERCISE_COUNT, CHOOSE_MUSCLE = range(2)