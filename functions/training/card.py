from utils.keyboard import get_edit_card_keyboard
from functions.training.core import сохранить_результат_упражнения, receive_exercise_count
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from datetime import date, datetime, timedelta
import matplotlib.pyplot as plt
import io
import re
from utils.data import load_user_data, write_user_data, get_progress_bar, разобрать_результат
import logging
from functions.base import get_main_menu_keyboard




# Показывает карточку пользователя с прогрессом
async def show_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logging.error("show_card вызван без update.message")
        return

    user_id = str(update.message.from_user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    data = load_user_data(user_id)

    # Если данных за сегодня нет или они пустые — ищем последнюю заполненную дату
    entry = data.get(today, {})
    if not any(entry.values()):
        previous_days = sorted(data.keys(), reverse=True)
        for date in previous_days:
            if isinstance(data[date], dict) and any(data[date].values()):
                today = date
                break
        else:
            if update.message:
                await update.message.reply_text("❌ Нет сохранённых данных.")
            return
    d = data[today]
    weight_prog = ""
    steps_prog = ""
    sleep_prog = ""
    calories_prog = ""

    goals = data.get("цели", {})
    desired_weight = goals.get("желаемый вес")
    desired_steps = goals.get("желаемые шаги")
    desired_sleep = goals.get("желаемый сон")
    desired_calories = goals.get("желаемые калории")

    # Получаем текущие значения
    weight = d.get("вес")
    steps = d.get("шаги")
    sleep = d.get("сон")
    calories = d.get("калории")

    weight_prog = steps_prog = sleep_prog = calories_prog = ""

    # Прогресс по весу
    try:
        # есть текущий вес и задана цель (не пустая и не "-")
        if weight and desired_weight not in (None, "", "-", "–"):
            # достаём числа из строк (могут быть "70 кг", "70.5", "70,5" и т.п.)
            desired_weight_value_str = _extract_number(str(desired_weight))
            start_weight_str = goals.get("стартовый вес", weight)
            start_weight_value_str = _extract_number(str(start_weight_str))
            current_weight_value_str = _extract_number(str(weight))

            # если хоть одно число не удалось вытащить — не считаем прогресс
            if not (desired_weight_value_str and start_weight_value_str and current_weight_value_str):
                raise ValueError("Не удалось извлечь числа для расчёта прогресса по весу")

            desired_weight_value = float(desired_weight_value_str)
            start_weight_value = float(start_weight_value_str)
            current_weight_value = float(current_weight_value_str)

            weight_diff = current_weight_value - desired_weight_value
            start_diff = start_weight_value - desired_weight_value

            if start_diff != 0:
                percent_weight = round((1 - weight_diff / start_diff) * 100)
                percent_weight = min(max(percent_weight, 0), 100)
                weight_prog = f"Вес: {get_progress_bar(percent_weight)} {percent_weight}%"
    except Exception as e:
        logging.warning("Ошибка при расчёте прогресса по весу: %s", e)
        weight_prog = "Вес: ❌ ошибка"


    # Прогресс по шагам
    try:
        if steps and desired_steps not in (None, "", "-", "–"):
            percent_steps = round(int(steps) / int(desired_steps) * 100)
            steps_prog = f"Шаги: {get_progress_bar(percent_steps)} {percent_steps}%"

    except Exception as e:
        logging.exception("Ошибка при расчёте прогресса по шагам: %s", e)
        steps_prog = "Шаги: ❌ ошибка"

    # Прогресс по сну
    try:
        if sleep and desired_sleep not in (None, "", "-", "–"):
            s_cur = float(sleep.split()[0])
            s_goal = float(desired_sleep.split()[0])
            percent_sleep = round(s_cur / s_goal * 100)
            percent_sleep = min(percent_sleep, 100)
            sleep_prog = f"Сон: {get_progress_bar(percent_sleep)} {percent_sleep}%"

    except Exception as e:
        logging.exception("Ошибка при расчёте прогресса по сну: %s", e)
        sleep_prog = "Сон: ❌ ошибка"

    # Прогресс по калориям
    try:
        if calories is not None and desired_calories not in (None, "", "-", "–"):
            percent_calories = round(int(calories) / int(desired_calories) * 100)
            calories_prog = f"Калории: {get_progress_bar(percent_calories)} {percent_calories}%"

    except Exception as e:
        logging.exception("Ошибка при расчёте прогресса по калориям: %s", e)
        calories_prog = "Калории: ❌ ошибка"


    # Собираем карточку
    card = f"""📅 Дата: {today}
🎯 Цель: {desired_weight} кг, {desired_steps} шагов, {desired_sleep} сна, {desired_calories} калорий

───────────────
🔹 Сейчас:
⚖️ Вес: {weight} кг
🏃 Шаги: {steps}
🔥 Калории: {d.get('калории', '–')}
💪 Тренировка: {d.get('тренировка', '–')}
🛌 Сон: {sleep}
───────────────
📈 Прогресс до цели:
{weight_prog}
{steps_prog}
{sleep_prog}
{calories_prog}
"""
    # Показываем упражнения, если они есть
    if "упражнения" in d:
        card += "\n🏋️ Упражнения:\n"
        for name, reps in d["упражнения"].items():
            card += f"{name.capitalize()}: {reps}\n"
    if update.message:
        await update.message.reply_text(
            card,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Изменить карточку", callback_data="edit_card_fields")]
            ])
        )



# Показывает график веса пользователя
async def plot_weight_graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_user_data(user_id)
    dates = []
    weights = []

    # Собираем даты и веса из данных пользователя
    for key in sorted(data.keys()):
        if key in ("цели", "username"):
            continue

        day_data = data[key]

        # Пропускаем, если это не словарь
        if not isinstance(day_data, dict):
            print(f"❗ Пропущена дата {key}, т.к. данные не словарь: {day_data}")
            continue

        weight = day_data.get("вес")
        if weight:
            # достаём число из строки веса ("70", "70 кг", "70,5" и т.п.)
            num_str = _extract_number(str(weight))
            if not num_str:
                continue
            try:
                weights.append(float(num_str))
                dates.append(key)  # key в формате "YYYY-MM-DD"
            except ValueError:
                continue

    if not weights:
        if update.message:
            await update.message.reply_text("📉 Нет данных о весе.")
        return

    # Преобразуем строки дат в объекты date, чтобы matplotlib не ругался
    clean_dates = []
    clean_weights = []

    for d, w in zip(dates, weights):
        try:
            # d в формате "YYYY-MM-DD"
            dt = datetime.strptime(d, "%Y-%m-%d").date()
        except Exception as e:
            logging.warning("Пропускаю дату %r в графике веса: %s", d, e)
            continue

        clean_dates.append(dt)
        clean_weights.append(w)

    if not clean_dates:
        if update.message:
            await update.message.reply_text("⚠️ Нет валидных данных по весу для построения графика.")
        return

    plt.figure(figsize=(6, 4))
    plt.plot(clean_dates, clean_weights, marker='o')
    plt.title("График изменения веса")
    plt.xlabel("Дата")
    plt.ylabel("Вес (кг)")
    plt.grid(True)

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)

    try:
        if update.message:
            await update.message.reply_photo(photo=buffer)
        elif update.callback_query and update.callback_query.message:
            # На случай вызова из callback
            await update.callback_query.message.reply_photo(photo=buffer)
        else:
            logging.error("plot_weight_graph: нет message или callback_query.message для отправки фото")
    finally:
        buffer.close()
        plt.close()



# Показывает статистику пользователя
async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logging.error("show_statistics вызван без update.message")
        return

    user_id = str(update.message.from_user.id)
    data = load_user_data(user_id)
    тренировки = 0
    даты_с_тренировками = []

    for дата, значение in data.items():
        if дата in ("цели", "username"):
            continue
        if isinstance(значение, dict) and "тренировка" in значение:
            тренировки += 1
            try:
                даты_с_тренировками.append(datetime.strptime(дата, "%Y-%m-%d").date())
            except Exception as e:
                logging.warning("Не удалось разобрать дату тренировки %s: %s", дата, e)
                continue

    даты_с_тренировками = sorted(set(даты_с_тренировками), reverse=True)
    подряд = 0
    today = datetime.today().date()

    for i in range(100):  # максимум 100 дней подряд
        day = today - timedelta(days=i)
        if day in даты_с_тренировками:
            подряд += 1
        else:
            break

    # Лучшие результаты
    лучшие = {}

    for дата, значение in data.items():
        if дата in ("цели", "username"):
            continue
        if not isinstance(значение, dict):
            print(f"❗ Пропущена дата {дата}, т.к. не словарь: {значение}")
            continue

        упражнения = значение.get("тренировка", {})
        if not isinstance(упражнения, dict):
            continue



        for название, результат in упражнения.items():
            try:
                _, _, вес = разобрать_результат(результат)
            except Exception as e:
                logging.exception("Ошибка при разборе результата упражнения '%s': %s", название, e)
                continue

            if вес is not None:
                try:
                    # сравнение с уже сохранённым лучшим результатом
                    if (
                        название not in лучшие
                        or вес > разобрать_результат(лучшие[название])[2]
                    ):
                        лучшие[название] = результат
                except Exception as e:
                    logging.exception(
                        "Ошибка при сравнении результатов упражнения '%s': %s",
                        название,
                        e,
                    )

    сообщение = (
        f"📈 Общее количество тренировок: {тренировки}\n"
        f"📅 Дней подряд с тренировками: {подряд}\n"
    )

    if лучшие:
        сообщение += "\n🏆 Лучшие результаты:\n"
        for название, результат in лучшие.items():
            сообщение += f"• {название.capitalize()}: {результат}\n"

    await update.message.reply_text(сообщение)


# ---------------- Работа с целями (мастер) ----------------

from telegram import CallbackQuery, Message
import logging
from utils.data import load_user_data


async def start_goals_edit(source, context):
    """Запускает пошаговый ввод целей (и с кнопки, и из /start)."""

    # 1️⃣ Определяем, что нам пришло: CallbackQuery или Message
    if isinstance(source, CallbackQuery):
        query = source
        user = query.from_user
        message = query.message

        # убираем "часики" на кнопке
        try:
            await query.answer()
        except Exception:
            pass

    elif isinstance(source, Message):
        user = source.from_user
        message = source

    else:
        logging.error("start_goals_edit вызван с неподдерживаемым типом: %s", type(source))
        return

    # 2️⃣ Грузим данные пользователя
    user_id = str(user.id)
    data = load_user_data(user_id)
    goals = data.get("цели", {})

    try:
        # Сохраняем текущие цели как временные в user_data
        context.user_data["goals_state"] = True
        context.user_data["goals_step"] = 1
        context.user_data["goals_tmp"] = {
            "желаемый вес": goals.get("желаемый вес"),
            "желаемые шаги": goals.get("желаемые шаги"),
            "желаемый сон": goals.get("желаемый сон"),
            "желаемые калории": goals.get("желаемые калории"),
            "стартовый вес": goals.get("стартовый вес"),
        }

        text = (
            "🎯 Обновим твои цели.\n"
            "Отвечай только цифрами.\n"
            "Если хочешь оставить старое значение — напиши «-».\n\n"
            "1/5. Введи желаемый вес в кг.\n"
            f"Сейчас: {goals.get('желаемый вес', 'не задано')}"
        )
        await message.reply_text(text)

    except Exception as e:
        logging.exception("Ошибка в start_goals_edit: %s", e)
        try:
            await message.reply_text(
                "⚠️ Не удалось запустить изменение целей. Попробуй ещё раз позже."
            )
        except Exception:
            pass



def _extract_number(text: str):
    """Достаёт первое число из строки (70, 70.5, 70,5)."""
    text = text.strip()
    m = re.search(r"\d+([.,]\d+)?", text)
    if not m:
        return None
    value = m.group(0).replace(",", ".")
    if "." in value:
        return value
    return str(int(value))


async def handle_goals_input(update, context):
    """Обрабатывает ввод пользователя на каждом шаге мастера целей."""

    if not update.message:
        logging.error("handle_goals_input вызван без update.message")
        return

    try:
        if not update.message:
            logging.error("handle_goals_input вызван без update.message")
            return
        
        text = update.message.text.strip()
        step = context.user_data.get("goals_step", 1)
        tmp = context.user_data.get("goals_tmp", {})

        async def ask_again(message: str):
            await update.message.reply_text(message)

        # Шаг 1 — желаемый вес
        if step == 1:
            if text != "-":
                value = _extract_number(text)
                if value is None:
                    await ask_again("Нужна только цифра, например: 70\nПопробуй ещё раз — желаемый вес (кг):")
                    return
                tmp["желаемый вес"] = value
            context.user_data["goals_step"] = 2
            await update.message.reply_text(
                "2/5. Введи цель по шагам в день.\n"
                f"Сейчас: {tmp.get('желаемые шаги', 'не задано')}\n"
                "Если хочешь оставить как есть — напиши «-»."
            )
            return

        # Шаг 2 — шаги
        if step == 2:
            if text != "-":
                value = _extract_number(text)
                if value is None:
                    await ask_again("Нужна только цифра, например: 10000\nПопробуй ещё раз — цель по шагам в день:")
                    return
                tmp["желаемые шаги"] = value
            context.user_data["goals_step"] = 3
            await update.message.reply_text(
                "3/5. Сколько часов сна хочешь в день?\n"
                f"Сейчас: {tmp.get('желаемый сон', 'не задано')}\n"
                "Если хочешь оставить как есть — напиши «-»."
            )
            return

        # Шаг 3 — сон
        if step == 3:
            if text != "-":
                value = _extract_number(text)
                if value is None:
                    await ask_again("Нужна только цифра, например: 8\nПопробуй ещё раз — цель по сну (часы):")
                    return
                tmp["желаемый сон"] = value
            context.user_data["goals_step"] = 4
            await update.message.reply_text(
                "4/5. Цель по калориям в день.\n"
                f"Сейчас: {tmp.get('желаемые калории', 'не задано')}\n"
                "Если хочешь оставить как есть — напиши «-»."
            )
            return

        # Шаг 4 — калории
        if step == 4:
            if text != "-":
                value = _extract_number(text)
                if value is None:
                    await ask_again("Нужна только цифра, например: 2500\nПопробуй ещё раз — цель по калориям в день:")
                    return
                tmp["желаемые калории"] = value
            context.user_data["goals_step"] = 5
            await update.message.reply_text(
                "5/5. Стартовый вес (для прогресса).\n"
                f"Сейчас: {tmp.get('стартовый вес', 'не задано')}\n"
                "Если хочешь оставить как есть — напиши «-»."
            )
            return

        # Шаг 5 — стартовый вес
        if step == 5:
            if text != "-":
                value = _extract_number(text)
                if value is None:
                    await ask_again("Нужна только цифра, например: 75\nПопробуй ещё раз — стартовый вес (кг):")
                    return
                tmp["стартовый вес"] = value

            # Сохраняем цели в JSON
            user_id = str(update.message.from_user.id)
            data = load_user_data(user_id)
            data["цели"] = tmp
            write_user_data(user_id, data)

            # Чистим состояние
            context.user_data.pop("goals_state", None)
            context.user_data.pop("goals_step", None)
            context.user_data.pop("goals_tmp", None)

            # 👉 Вот тут отправляем сообщение + показываем главное меню
            await update.message.reply_text(
                "✅ Цели сохранены! Можешь снова открыть карточку, чтобы посмотреть прогресс.",
                reply_markup=get_main_menu_keyboard(),
            )
            return
        
        
    except Exception as e:
        logging.exception("Ошибка в handle_goals_input: %s", e)
        try:
            await update.message.reply_text(
                "⚠️ Что-то пошло не так при изменении целей. Попробуй позже."
            )
        except Exception:
            pass
        # На всякий пожарный сбросим состояние мастера
        context.user_data.pop("goals_state", None)
        context.user_data.pop("goals_step", None)
        context.user_data.pop("goals_tmp", None)
    
    


# Редактирует карточку пользователя
async def edit_card_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        logging.error("edit_card_callback вызван без callback_query")
        return
    try:
        await query.answer()

        # Кнопка "Цели" — запускаем мастер ввода целей
        if query.data == "edit_goals":
            await start_goals_edit(query, context)
            return

        # Остальные кнопки — обычное редактирование полей за сегодня
        context.user_data["state"] = "card_edit"
        await query.message.reply_text(
            "Выбери, что хочешь изменить:",
            reply_markup=get_edit_card_keyboard()
        )

    except Exception as e:
        logging.exception("Ошибка в edit_card_callback: %s", e)
        try:
            await query.message.reply_text(
                "⚠️ Не удалось открыть меню редактирования. Попробуй ещё раз."
            )
        except Exception:
            pass

# ---------------- Универсальное редактирование полей карточки ----------------

FIELD_CONFIG = {
    "weight": {
        "field": "вес",
        "prompt": "Введите новый вес (кг):",
    },
    "steps": {
        "field": "шаги",
        "prompt": "Введите новое количество шагов:",
    },
    "sleep": {
        "field": "сон",
        "prompt": "Введите новое количество сна (например, 8 ч):",
    },
    "calories": {
        "field": "калории",
        "prompt": "Введите новое количество калорий:",
    },
}


async def edit_field_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Универсальный обработчик для кнопок edit_field:... (вес, шаги, сон, калории)."""

    query = update.callback_query
    if not query:
        logging.error("edit_field_callback вызван без callback_query")
        return

    try:
        await query.answer()

        data = query.data  # например: "edit_field:weight"
        try:
            _, key = data.split(":", 1)
        except ValueError:
            await query.message.reply_text("⚠️ Не удалось определить, что нужно изменить.")
            return

        config = FIELD_CONFIG.get(key)
        if not config:
            await query.message.reply_text("⚠️ Неизвестное поле для редактирования.")
            return

        # Сохраняем, какое поле редактируем
        context.user_data["editing_field"] = config["field"]

        # Переспрашиваем пользователя
        await query.edit_message_text(config["prompt"])

    except Exception as e:
        logging.exception("Ошибка в edit_field_callback: %s", e)
        try:
            await query.message.reply_text(
                "⚠️ Не удалось начать редактирование поля. Попробуй ещё раз."
            )
        except Exception:
            pass


# Запрашивает у пользователя новое описание тренировки
async def edit_workout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        logging.error("edit_workout_callback вызван без callback_query")
        return

    try:
        await query.answer()
        context.user_data["editing_field"] = "тренировка"
        await query.edit_message_text("Введите описание новой тренировки:")
    except Exception as e:
        logging.exception("Ошибка в edit_workout_callback: %s", e)
        try:
            await query.message.reply_text(
                "⚠️ Не удалось начать редактирование тренировки. Попробуй ещё раз."
            )
        except Exception:
            pass



# Сохраняет новое значение для выбранного поля
async def save_new_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logging.error("save_new_value вызван без update.message")
        return

    user_id = str(update.message.from_user.id)
    new_value = update.message.text
    editing_field = context.user_data.get("editing_field")

    if editing_field:
        try:
            data = load_user_data(user_id)
            today = str(date.today())
            if today not in data:
                data[today] = {}
            data[today][editing_field] = new_value
            write_user_data(user_id, data)
            await update.message.reply_text(
                f"✅ Значение поля '{editing_field}' обновлено!"
            )
        except Exception as e:
            logging.exception("Ошибка при сохранении нового значения '%s': %s", editing_field, e)
            await update.message.reply_text(
                "⚠️ Не удалось сохранить новое значение. Попробуй позже."
            )
        finally:
            context.user_data.pop("editing_field", None)

    else:
        if update.message:
            await update.message.reply_text("⚠️ Не выбрано, что изменить.")
    if "input_sequence" in context.user_data:
        await ask_next_field(update, context)


# Показывает карту тренировок пользователя
async def show_workout_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logging.error("show_workout_card вызван без update.message")
        return

    try:
        user_id = str(update.message.from_user.id)
        data = load_user_data(user_id)
    except Exception as e:
        logging.exception("Ошибка при загрузке данных для show_workout_card: %s", e)
        await update.message.reply_text("⚠️ Не удалось загрузить тренировки.")
        return


    dates = sorted(data.keys(), reverse=True)
    for date in dates:
        if "тренировка" in data[date]:
            workout = data[date]["тренировка"]
            if isinstance(workout, dict):
                message = f"📋 Тренировка за {date}:\n\n"
                for name, reps in workout.items():
                    message += f"{name.capitalize()}: {reps}\n"
                if update.message:
                    await update.message.reply_text(message)
                return
            else:
                if update.message:
                    await update.message.reply_text(f"📋 Тренировка за {date}: {workout}")
                return

    if update.message:
        await update.message.reply_text("❌ У тебя нет сохранённых тренировок.")


# Запрашивает у пользователя следующее поле для ввода данных
async def ask_next_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sequence = context.user_data.get("input_sequence", [])
    if not sequence:
        await update.message.reply_text("✅ Все данные введены!")
        return
    next_field = sequence.pop(0)
    context.user_data["editing_field"] = next_field
    prompts = {
        "вес": "Введите вес (кг):",
        "шаги": "Введите количество шагов:",
        "калории": "Введите количество калорий:",
        "сон": "Сколько часов сна?:"
    }
    await update.message.reply_text(prompts.get(next_field, "Введите значение:"))

# Начинает последовательный ввод данных от пользователя
async def start_sequential_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["input_sequence"] = ["вес", "шаги", "калории", "сон"]
    await ask_next_field(update, context)


async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logging.error("universal_handler вызван без update.message")
        return
    
    try:
        state = context.user_data.get("state")
        text = update.message.text
        user_id = str(update.message.from_user.id)

        # --- Мастер изменения целей ---
        if context.user_data.get("goals_state"):
            return await handle_goals_input(update, context)

        # --- Обработка редактирования карточки ---
        if state == "card_edit":
            return await save_new_value(update, context)

        # --- Обработка результата упражнения ---
        elif state == "exercise_result":
            return await сохранить_результат_упражнения(update, context)

        # --- Ввод количества повторений ---
        elif state == "count_input":
            return await receive_exercise_count(update, context)

        # --- Неопознанное состояние ---
        else:
            await update.message.reply_text("Пожалуйста, выбери действие через кнопки.")

    except Exception as e:
        logging.exception("Ошибка в universal_handler: %s", e)
        try:
            await update.message.reply_text(
                "⚠️ При обработке ввода произошла ошибка. Попробуй ещё раз."
            )
        except Exception:
            pass
