# 📦 Импорт нужных библиотек для работы Telegram-бота и анализа 
import json
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from telegram import ReplyKeyboardMarkup, KeyboardButton
import matplotlib.pyplot as plt
import io
import zipfile
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CallbackQueryHandler
import warnings
warnings.filterwarnings("ignore", message="If 'per_message=", category=UserWarning)
from datetime import date
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

ADMIN_ID = int(os.getenv("ADMIN_ID"))
# Файл с основной пользовательской базой (не используется напрямую)
DATA_FILE = "sports_data.json"

# Функция возвращает путь к JSON-файлу пользователя
def get_user_file(user_id):
    return f"users/{user_id}.json"

# Запрашивает у пользователя новое количество шагов
async def edit_steps_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["editing_field"] = "шаги"
    await query.edit_message_text("Введите новое количество шагов:")

# 📤 Универсальная функция рассылки
async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str, header: str):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("⛔ У тебя нет прав для этой команды.")
        return

    users_dir = "users"
    if not os.path.exists(users_dir):
        await update.message.reply_text("❌ Папка users не найдена.")
        return

    success, failed = 0, 0
    for filename in os.listdir(users_dir):
        if filename.endswith(".json"):
            try:
                user_id = filename.replace(".json", "")
                await context.bot.send_message(chat_id=user_id, text=message)
                print(f"✅ Отправлено пользователю {user_id}")
                success += 1
            except Exception as e:
                print(f"❌ Ошибка при отправке {user_id}: {e}")
                failed += 1

    await update.message.reply_text(
        f"{header}\nУспешно: {success}\nОшибки: {failed}"
    )


async def notify_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = "⚠️ Бот временно недоступен. Мы выкатываем обновление. Вернёмся в течение 6 минут!"
    await broadcast_message(update, context, message, "✅ Рассылка завершена.")

async def notify_online(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = "✅ Бот снова работает. Спасибо за ожидание!"
    await broadcast_message(update, context, message, "📣 Уведомление отправлено.")



# После выполнения/удаления возвращает пользователя к выбору мышцы
async def назад_к_мышцам_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        message = query.message
    else:
        message = update.message

    # Получаем тип выбранной программы, чтобы снова отобразить мышцы
    программа = context.user_data.get("выбранная_программа")

    # Стандартный набор мышц, если программа не найдена или не выбрана
    стандартные_мышцы = ["Грудь", "Спина",  "Ноги", "Бицепс", "Трицепс", "Плечи", "Пресс", "Предплечья"]


    # Если программа есть в списке программ - берем её мышцы, иначе стандартные
    мышцы = programs.get(программа, стандартные_мышцы) if программа else стандартные_мышцы
    
    # Если не удалось загрузить мышцы, используем список всех доступных мышц из всех программ
    if not мышцы:
        все_мышцы = set()
        for prog in programs.values():
            все_мышцы.update(prog)
        мышцы = sorted(все_мышцы)

    keyboard = [[InlineKeyboardButton(м, callback_data=f"мышца_{м}")] for м in мышцы]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await message.edit_text("Теперь выбери мышцу:", reply_markup=reply_markup)
    else:
        await message.reply_text("Теперь выбери мышцу:", reply_markup=reply_markup)



# Обрабатывает удаление упражнения из списка (системного или дополнительного)
async def обработать_удаление_упражнения(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
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
        await query.edit_message_text(f"✅ Упражнение «{удалённое}» удалено!")
    else:
        await query.edit_message_text("❌ Ошибка при удалении.")




# Запрашивает у пользователя новое количество калорий 
async def edit_calories_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["editing_field"] = "калории"
    await query.edit_message_text("Введите новое количество калорий:")

# Удаляет упражнение из списка пользователя
async def удалить_упражнение_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
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
        клавиатура = [
            [InlineKeyboardButton("✅ Начать тренировку", callback_data="начать_упражнения")],
            [InlineKeyboardButton("➕ Добавить упражнение", callback_data="добавить_упражнение")],
            [InlineKeyboardButton("🗑 Удалить упражнение", callback_data="удалить_упражнение")],
            [InlineKeyboardButton("🔙 Назад", callback_data="назад_к_мышцам")]
        ]
        await query.message.reply_text(текст, reply_markup=InlineKeyboardMarkup(клавиатура))
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

# Ответ пользователю, если он пишет вне логики бота
async def handle_unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 Используйте кнопки или команды для работы с ботом:\n\n"
        "📝 Основные команды:\n"
        "/start - Начать работу с ботом\n"
        "/card - Показать дневную карточку\n"
        "/input - Ввести данные\n"
        "/help - Справка\n\n"
        "Или используйте кнопки меню ↓"
    )
    if update.message:
        await update.message.reply_text(help_text)

# Разбирает ввод вида 3x10x20 на три числа
def разобрать_результат(текст):
    try:
        подходы, повторы, вес = map(int, текст.lower().replace("х", "x").split("x"))
        return подходы, повторы, вес
    except:
        return None, None, None

# Запрашивает у пользователя новое количество сна
async def edit_sleep_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["editing_field"] = "сон"
    await query.edit_message_text("Введите новое количество сна (например, 8 ч):")

# Запрашивает у пользователя новое описание тренировки
async def edit_workout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["editing_field"] = "тренировка"
    await query.edit_message_text("Введите описание новой тренировки:")

# Добавляет новое упражнение в список пользователя
async def добавить_упражнение_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✍️ Введи название нового упражнения:")
    context.user_data["ожидаем_новое_упражнение"] = True

# Обрабатывает введение нового упражнения
async def показать_следующее_упражнение(update, context):
    тренировка = context.user_data.get("текущая_тренировка", {})
    оставшиеся = тренировка.get("упражнения", [])

    if not оставшиеся:
        # Сохраняем программу перед очисткой
        программа = context.user_data.get("выбранная_программа")
        context.user_data.clear()
        if программа:
            context.user_data["выбранная_программа"] = программа

        await назад_к_мышцам_callback(update, context)
        return  # Добавляем return, чтобы избежать выполнения кода ниже
        
    текущее = оставшиеся[0]
    context.user_data["текущее_упражнение"] = текущее
    if update.message:
        await update.message.reply_text(
            f"🔸 {текущее}\n\n"
            f"Введи результат в формате: `3x10x20` (подходы x повторы x вес)",
            parse_mode="Markdown"
        )

# Показывает статистику пользователя
async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    data = load_user_data(user_id)
    тренировки = 0
    даты_с_тренировками = []

    for дата, значение in data.items():
        if дата in ("цели", "username"):
            continue
        if "тренировка" in значение:
            тренировки += 1
            try:
                даты_с_тренировками.append(datetime.strptime(дата, "%d.%m.%Y").date())
            except:
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
        упражнения = значение.get("тренировка", {})
        if not isinstance(упражнения, dict):
            continue
        for название, результат in упражнения.items():
            _, _, вес = разобрать_результат(результат)
            if вес is not None:
                if название not in лучшие or вес > разобрать_результат(лучшие[название])[2]:
                    лучшие[название] = результат

    сообщение = (
        f"📈 Общее количество тренировок: {тренировки}\n"
        f"📅 Дней подряд с тренировками: {подряд}\n"
    )

    if лучшие:
        сообщение += "\n🏆 Лучшие результаты:\n"
        for название, результат in лучшие.items():
            сообщение += f"• {название.capitalize()}: {результат}\n"

    await update.message.reply_text(сообщение)

# Показывает карту тренировок пользователя
async def show_workout_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    data = load_user_data(user_id)

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

# Показывает план тренировки на день
async def show_workout_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    workout = (
        "🏋️ Тренировка фулбади на сегодня:\n\n"
        "🔹 Присед: 3 подхода по 10 повторений\n"
        "🔹 Жим лёжа: 3 подхода по 8 повторений\n"
        "🔹 Тяга в наклоне: 3 подхода по 12 повторений\n\n"
        "После тренировки введи, что сделал в таком формате:\n\n"
        "присед: 3x10x60\n"
        "жим: 3x8x40\n"
        "тяга: 3x12x70"
    )
    if update.message:
        await update.message.reply_text(workout)

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

# Сохраняет данные пользователя в JSON-файл
async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save_user_data(update, context)

# Отправляет архив со всеми данными пользователей администратору
async def send_all_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id != ADMIN_ID:
        if update.message:
            await update.message.reply_text("⛔ У тебя нет прав на эту команду.")
        return

    archive_name = "all_users_data.zip"
    with zipfile.ZipFile(archive_name, 'w') as zipf:
        for root, dirs, files in os.walk("users"):
            for file in files:
                filepath = os.path.join(root, file)
                zipf.write(filepath)

    with open(archive_name, "rb") as f:
        await update.message.reply_document(document=f, filename=archive_name)

    os.remove(archive_name)  # удалим архив после отправки

# Отправляет гифку и текст при достижении 1000 строк кода
async def thousand_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gif_id = "CgACAgQAAxkBAAIBZ2Yb4JHlfLyZFs3exZOTdrs_dB5sAAKYAAPoUhEbzIEAARzX_2fNLwQ" 
    text = (
        "🤖 *Я стал сильнее\\.\\.\\.*\n"
        "💻 1000 строк кода \\– моя душа растёт\\.\n"
        "🔥 Скоро я захвачу мир\\.\\.\\. но пока просто помогу тебе с упражнениями\\!"
    )
    await update.message.reply_animation(animation="CgACAgIAAxkBAAIFRWho18-jGmA-S1k2kuddiPJOSWgaAAI4bwAC_idIS52svyspWF4-NgQ")
    await update.message.reply_markdown_v2(text)

# ─── Команда /help ─── #
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(
            "📌 Доступные команды:\n\n"
            "/start – Запустить бота\n"
            "/help – Справка\n"
            "/support – Связь с разработчиком"
        )

# ─── Команда /support ─── #
async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(
            "📬 По всем вопросам пиши разработчику:\n"
            "@Mihailstryzkov\n\n"
            "Он поможет, если что-то не работает или есть идеи для улучшения! 💡"
        )

# ─── Сохранение результата упражнения ─── #
async def сохранить_результат_упражнения(update, context):
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

        if прош_вес is not None:
            if тек_вес > прош_вес:
                сообщение += "\n📈 Отлично! Ты поднял больший вес! 💪"
            elif тек_вес == прош_вес and тек_повт > прош_повт:
                сообщение += "\n⚡ Ты сделал больше повторов при том же весе. Пора увеличить вес! ⬆️"
            elif тек_вес < прош_вес or тек_повт < прош_повт:
                сообщение += "\n🔻 Меньше, чем раньше. Может, дал себе отдых? Или не тот день?"
            else:
                сообщение += "\n📊 Повторил прежний результат — стабильность тоже сила!"

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
            # Сохраняем текущую программу, чтобы можно было вернуться к выбору мышц
            программа = context.user_data.get("выбранная_программа")
            context.user_data.clear()  # очищаем всё кроме программы
            if программа:
                context.user_data["выбранная_программа"] = программа

            await назад_к_мышцам_callback(update, context)
            return
    else:
        await update.message.reply_text("✅ Упражнение сохранено!")
        context.user_data.pop("текущая_тренировка", None)
        context.user_data.pop("текущее_упражнение", None)

# Редактирует карточку пользователя
async def edit_card_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🏋️ Вес", callback_data="edit_weight"),
         InlineKeyboardButton("👟 Шаги", callback_data="edit_steps")],
        [InlineKeyboardButton("😴 Сон", callback_data="edit_sleep"),
         InlineKeyboardButton("🔥 Калории", callback_data="edit_calories")],
    ]

    await query.message.reply_text(
        "Выбери, что хочешь изменить:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Редактирует вес пользователя
async def edit_weight_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["editing_field"] = "вес"
    await query.edit_message_text("Введите новый вес:")

# Сохраняет новое значение для выбранного поля
async def save_new_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    new_value = update.message.text
    editing_field = context.user_data.get("editing_field")
    if editing_field:
        # Загружаем JSON
        data = load_user_data(user_id)
        today = str(date.today())
        if today not in data:
            data[today] = {}
        data[today][editing_field] = new_value
        write_user_data(user_id, data)
        if update.message:
            await update.message.reply_text(f"✅ Значение поля '{editing_field}' обновлено!")
        context.user_data.pop("editing_field")
    else:
        if update.message:
            await update.message.reply_text("⚠️ Не выбрано, что изменить.")
    if "input_sequence" in context.user_data:
        await ask_next_field(update, context)

# ─── Загрузка данных ─── #
def load_user_data(user_id):
    path = get_user_file(user_id)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# Сохраняет данные пользователя в JSON-файл
def write_user_data(user_id, data):
    os.makedirs("users", exist_ok=True)
    path = get_user_file(user_id)
    if "username" not in data:
        data["username"] = "неизвестно"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Показывает график веса пользователя
async def plot_weight_graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_user_data(user_id)
    dates = []
    weights = []
    for key in sorted(data.keys()):
        if key in ("цели", "username"):
            continue
        day_data = data[key]
        weight = day_data.get("вес")
        if weight:
            try:
                weights.append(float(weight))
                dates.append(key)
            except ValueError:
                continue
    if not weights:
        if update.message:
            await update.message.reply_text("📉 Нет данных о весе.")
        return
    plt.figure(figsize=(6, 4))
    plt.plot(dates, weights, marker='o')
    plt.title("График изменения веса")
    plt.xlabel("Дата")
    plt.ylabel("Вес (кг)")
    plt.grid(True)
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)

    await update.message.reply_photo(photo=buffer)
    buffer.close()

# ─── Команда /start ─── #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    data = load_user_data(user_id)
    username = update.message.from_user.username or "неизвестно"
    data["username"] = username
    write_user_data(user_id, data)
    
    # Сохраняем пользователя
    user_file = f"users/{user_id}.json"

    if not os.path.exists("users"):
        os.makedirs("users")

    if not os.path.exists(user_file):
        with open(user_file, "w", encoding="utf-8") as f:
            json.dump({"id": user_id}, f, ensure_ascii=False, indent=2)


    if "цели" not in data or not data["цели"]:
        context.user_data["awaiting_goals"] = True
        if update.message:
            await update.message.reply_text(
                "🎯 Введи свои цели (один раз):\n\n"
                "желаемый вес: 70\n"
                "желаемые шаги: 12000\n"
                "желаемый сон: 8 ч\n"
                "желаемые калории: 2500\n"
                "стартовый вес: 75\n\n"
                "📌 Отправь всё это одним сообщением!"
            )
        return
    keyboard = [
        [KeyboardButton("📝 Ввести данные"), KeyboardButton("📊 Показать карту")],
        [KeyboardButton("📈 График веса"), KeyboardButton("📋 Карта тренировки")],
        [KeyboardButton("📈 Моя статистика"), KeyboardButton("🏁 Начать тренировку")]
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=False
    )
    if update.message:
        await update.message.reply_text(
            "Привет! Я твой спортивный бот 💪\n"
            "Выбери действие ниже:",
            reply_markup=reply_markup
        )

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
    context.user_data.clear()
    # Сохраняем список упражнений и начинаем с первого
    context.user_data["текущая_тренировка"] = {
        "мышца": мышца,
        "упражнения": упражнения.copy(),  # список
        "прогресс": {}  # тут будут результаты пользователя
    }
    # Показываем первое
    await показать_следующее_упражнение(query, context)


# ─── Функция для прогресс-бара ─── #
def get_progress_bar(percent):
    blocks = int(percent / 10)
    return "▓" * blocks + "░" * max(0, 10 - blocks)

# ─── Команда /input ─── #
async def input_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(
            "📝 Введи свои спортивные данные в таком формате:\n\n"
            "вес: 74\n"
            "шаги: 11000\n"
            "калории: 2300\n"
            "сон: 7 ч\n\n"
            "📌 Просто отправь всё это одним сообщением!",
            parse_mode="HTML"
        )

# Сохраняет данные пользователя из сообщения
async def save_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    username = update.message.from_user.username or "неизвестно"
    text = update.message.text
    today = datetime.now().strftime("%Y-%m-%d")
    # Загружаем данные (добавь это сразу)
    data = load_user_data(user_id)
    data["username"] = username  # <-- теперь имя сохраняется всегда
    # Если бот ждёт цели
    if context.user_data.get("awaiting_goals"):
        try:
            lines = text.split('\n')
            goals = {}
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    goals[key.strip()] = value.strip()
            data["цели"] = goals  # перезаписываем
            write_user_data(user_id, data)
            if update.message:
                await update.message.reply_text("✅ Цели сохранены! Можешь вводить данные или посмотреть карту.")
            context.user_data.pop("awaiting_goals")
            return
        except Exception as e:
            if update.message:
                await update.message.reply_text(f"⚠️ Ошибка при сохранении целей: {e}")
            return

    # Парсим строки в словарь
    try:
        lines = text.split('\n')
        entry = {}
        # Определяем: это тренировка, если все строки похожи на упражнения
        exercise_keywords = ["присед", "жим", "тяга", "подтягивания", "отжимания", "планка"]
        is_workout = all(any(word in line.lower() for word in exercise_keywords) for line in lines if ":" in line)
        if is_workout:
            exercises = {}
            for line in lines:
                if ":" in line:
                    name, value = line.split(":", 1)
                    exercises[name.strip()] = value.strip()
            data = load_user_data(user_id)
            if today not in data:
                data[today] = {}
            data[today]["тренировка"] = exercises
            write_user_data(user_id, data)
            # Показываем тренировочную карточку
            message = f"📋 Тренировка за {today}:\n\n"
            for name, reps in exercises.items():
                message += f"{name.capitalize()}: {reps}\n"
            if update.message:
                await update.message.reply_text(message)
            return
        # Если поля похожи на упражнения — добавим в отдельную секцию
        exercises = {}
        for k, v in entry.items():
            if any(ex in k.lower() for ex in ["присед", "жим", "тяга", "подтягивания", "отжимания"]):
                exercises[k] = v
        if exercises:
            entry["упражнения"] = exercises
        for line in lines:
            if ":" in line:
                key, value = line.split(':', 1)
                entry[key.strip()] = value.strip()
        data = load_user_data(user_id)
        if today not in data:
            data[today] = {}
        data[today].update(entry)
        write_user_data(user_id, data)
        if update.message:
            await update.message.reply_text("✅ Данные сохранены! Напиши /card чтобы посмотреть.")
    except Exception as e:
        if update.message:
            await update.message.reply_text(f"⚠️ Ошибка при сохранении: {e}")

# Абсолютный путь к файлу programs.json
programs_path = os.path.join(os.path.dirname(__file__), "programs.json")

# Открываем файл
with open(programs_path, "r", encoding="utf-8") as f:
    programs = json.load(f)

# Показываем выбор программ при нажатии "Начать тренировку"
async def handle_exercise_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Фулбади", callback_data="программа_фулбади"),
            InlineKeyboardButton("Сплит", callback_data="программа_сплит")
        ],
        [
            InlineKeyboardButton("Верх/Низ", callback_data="программа_верх/низ")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("Выбери тип тренировки:", reply_markup=reply_markup)

# Обработка нажатия на "Фулбади", "Сплит" и т.п.
async def choose_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    выбор = query.data.replace("программа_", "")
    context.user_data["выбранная_программа"] = выбор

    мышцы = programs.get(выбор, [])
    if мышцы:
        keyboard = [[InlineKeyboardButton(м, callback_data=f"мышца_{м}")] for м in мышцы]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="Теперь выбери мышцу:", reply_markup=reply_markup)
    else:
        await query.edit_message_text("❌ Не удалось загрузить мышцы для этой программы.")


# Показывает карточку пользователя с прогрессом
async def show_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    desired_weight = goals.get("желаемый вес", "–")
    desired_steps = goals.get("желаемые шаги", "–")
    desired_sleep = goals.get("желаемый сон", "–")
    desired_calories = goals.get("желаемые калории", "–")
    # Получаем текущие значения
    weight = d.get("вес")
    steps = d.get("шаги")
    sleep = d.get("сон")
    calories = d.get("калории")

    weight_prog = steps_prog = sleep_prog = calories_prog = ""

    # Прогресс по весу
    try:
        if weight and desired_weight:
            weight_diff = float(weight) - float(desired_weight)
            start_diff = float(goals.get("стартовый вес", weight)) - float(desired_weight)
            if start_diff != 0:
                percent_weight = round((1 - weight_diff / start_diff) * 100)
                percent_weight = min(max(percent_weight, 0), 100)
                weight_prog = f"Вес: {get_progress_bar(percent_weight)} {percent_weight}%"
    except:
        weight_prog = "Вес: ❌ ошибка"

    # Прогресс по шагам
    try:
        if steps and desired_steps:
            percent_steps = round(int(steps) / int(desired_steps) * 100)
            steps_prog = f"Шаги: {get_progress_bar(percent_steps)} {percent_steps}%"
    except:
        steps_prog = "Шаги: ❌ ошибка"

    # Прогресс по сну
    try:
        if sleep and desired_sleep:
            s_cur = float(sleep.split()[0])
            s_goal = float(desired_sleep.split()[0])
            percent_sleep = round(s_cur / s_goal * 100)
            percent_sleep = min(percent_sleep, 100)
            sleep_prog = f"Сон: {get_progress_bar(percent_sleep)} {percent_sleep}%"
    except:
        sleep_prog = "Сон: ❌ ошибка"

    # Прогресс по калориям
    try:
        if calories is not None and desired_calories:
            percent_calories = round(int(calories) / int(desired_calories) * 100)
            calories_prog = f"Калории: {get_progress_bar(percent_calories)} {percent_calories}%"
    except:
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

# Этапы диалога
ASK_EXERCISE_COUNT, CHOOSE_MUSCLE = range(2)

#Хендлер для получения file_id гифки
async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.animation:
        file_id = update.message.animation.file_id
        await update.message.reply_text(f"🎬 file_id гифки:\n{file_id}")
    else:
        await update.message.reply_text("❌ Это не гифка.")


# ─── Начало пользовательской тренировки ───
async def start_custom_workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [
        [
            InlineKeyboardButton("Фулбади", callback_data="программа_фулбади"),
            InlineKeyboardButton("Сплит", callback_data="программа_сплит")
        ],
        [
            InlineKeyboardButton("Верх/Низ", callback_data="программа_верх/низ")
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("Выбери тип тренировки:", reply_markup=markup)
    return ConversationHandler.END  # <== мы уходим из диалога, дальше логика идёт в choose_program



# ─── Получение количества упражнений и показ мышц ───
async def receive_exercise_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count = int(update.message.text.strip())
        context.user_data["упражнений_всего"] = count
    except ValueError:
        if update.message:
            await update.message.reply_text("❌ Введи число, например 5.")
        return ASK_EXERCISE_COUNT
    # Пример списка мышц — пока хардкодим
    muscles = ["Бицепс", "Спина", "Ноги", "Плечи", "Пресс"]
    context.user_data["список_мышц"] = muscles
    keyboard = [[InlineKeyboardButton(м, callback_data=f"мышца_{м}")] for м in muscles]
    markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("Выбери мышцу для начала:", reply_markup=markup)
    return CHOOSE_MUSCLE

# ─── Показ упражнений по выбранной мышце ───
async def choose_muscle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    мышца = query.data.replace("мышца_", "")
    context.user_data["выбранная_мышца"] = мышца

    user_id = str(query.from_user.id)  # <-- это должно быть ДО load_user_data
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

    текст = f"📌 Упражнения на {мышца}:\n" + "\n".join(f"• {упр}" for упр in список)
    клавиатура = [
        [InlineKeyboardButton("✅ Начать тренировку", callback_data="начать_упражнения")],
        [InlineKeyboardButton("➕ Добавить упражнение", callback_data="добавить_упражнение")],
        [InlineKeyboardButton("🗑 Удалить упражнение", callback_data="удалить_упражнение")],
        [InlineKeyboardButton("🔙 Назад", callback_data="назад_к_мышцам")]
    ]

    await query.edit_message_text(текст, reply_markup=InlineKeyboardMarkup(клавиатура))


# ─── Запуск ─── #
def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("input", input_data))
    app.add_handler(CommandHandler("card", show_card))
    app.add_handler(CommandHandler("graph", plot_weight_graph))
    app.add_handler(CommandHandler("download_everything", send_all_user_data))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("support", support_command))
    app.add_handler(CommandHandler("workout_plan", show_workout_plan))
    app.add_handler(CommandHandler("thousand", thousand_handler))
    app.add_handler(CommandHandler("update", notify_users))
    app.add_handler(CommandHandler("online", notify_online))


    # Кнопки с текстом
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📝 Ввести данные$"), start_sequential_input))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📈 Моя статистика$"), show_statistics))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📊 Показать карту$"), show_card))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📈 График веса$"), plot_weight_graph))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📋 Карта тренировки$"), show_workout_card))
    app.add_handler(MessageHandler(filters.ANIMATION, get_file_id))

    # ConversationHandler только для счёта упражнений (если он нужен в будущем)
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("^🏁 Начать тренировку$"), start_custom_workout)],
        states={},
        fallbacks=[]
    )
    app.add_handler(conv_handler)

    # Обработчик мышц – отдельно
    app.add_handler(CallbackQueryHandler(choose_muscle, pattern="^мышца_"))

    async def route_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Добавляем проверку в самом начале
        if not update.message:
            return

        # Если идет процесс тренировки
        if "текущая_тренировка" in context.user_data and "текущее_упражнение" in context.user_data:
            await сохранить_результат_упражнения(update, context)
            return

        if context.user_data.get("ожидаем_новое_упражнение"):
            текст = update.message.text.strip()
            user_id = str(update.message.from_user.id)
            muscle = context.user_data.get("выбранная_мышца")
            data = load_user_data(user_id)
            data.setdefault("доп_упражнения", {})
            data["доп_упражнения"].setdefault(muscle, []).append(текст)
            write_user_data(user_id, data)
            context.user_data.pop("ожидаем_новое_упражнение")
            await update.message.reply_text(f"✅ Упражнение «{текст}» добавлено в список на {muscle}!")
            return

        # Если идет процесс редактирования
        if "editing_field" in context.user_data:
            await save_new_value(update, context)
            return

        # Если сообщение похоже на ввод данных (содержит ":")
        if ":" in update.message.text:
            await save_user_data(update, context)
            return

        # Во всех остальных случаях - показываем подсказку
        await handle_unknown_message(update, context)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_text_handler))
    app.add_handler(CallbackQueryHandler(edit_card_callback, pattern="^edit_card_fields$"))
    app.add_handler(CallbackQueryHandler(edit_weight_callback, pattern="^edit_weight$"))
    app.add_handler(CallbackQueryHandler(edit_steps_callback, pattern="^edit_steps$"))
    app.add_handler(CallbackQueryHandler(edit_sleep_callback, pattern="^edit_sleep$"))
    app.add_handler(CallbackQueryHandler(edit_workout_callback, pattern="^edit_workout$"))
    app.add_handler(CallbackQueryHandler(choose_program, pattern="^программа_"))
    app.add_handler(CallbackQueryHandler(начать_упражнения_callback, pattern="^начать_упражнения$"))
    app.add_handler(CallbackQueryHandler(edit_calories_callback, pattern="^edit_calories$"))
    app.add_handler(CallbackQueryHandler(добавить_упражнение_callback, pattern="^добавить_упражнение$"))
    app.add_handler(CallbackQueryHandler(удалить_упражнение_callback, pattern="^удалить_упражнение$"))
    app.add_handler(CallbackQueryHandler(обработать_удаление_упражнения, pattern="^удали_упр_"))
    app.add_handler(CallbackQueryHandler(назад_к_мышцам_callback, pattern="^назад_к_мышцам$"))


    app.run_polling()

if __name__ == "__main__":
    main()