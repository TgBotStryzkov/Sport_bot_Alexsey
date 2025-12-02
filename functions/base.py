# 📦 Telegram
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)
from functions.send import send_all_user_data, show_users_count, send_commands_file
import json
import os
from utils.data import ensure_user_file_exists


# 🧠 Локальные утилиты
from utils.data import (
    load_user_data,
    write_user_data,
    save_user_data
)
from utils.keyboard import (
    get_main_menu
)

# 🏋️‍♂️ Обработка упражнений и тренировок
from functions.training.core import (
    сохранить_результат_упражнения,
    choose_program,
    назад_к_мышцам_callback,
    удалить_упражнение_callback,
    добавить_упражнение_callback,
    choose_muscle,
    start_custom_workout,
    обработать_удаление_упражнения
)

from functions.training.card import (
    start_sequential_input,
    save_new_value,
    edit_card_callback,
    edit_workout_callback,
    show_card,
    show_workout_card,
    show_statistics,
    plot_weight_graph,
    start_goals_edit,   
    handle_goals_input,
    edit_field_callback
)



# 🛠 Прочие функции
from functions.notify import (
    notify_users,
    notify_online
)



# Сохраняет данные пользователя в JSON-файл
async def universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await save_user_data(update, context)
    except Exception as e:
        # здесь не падаем, просто логируем
        import logging
        logging.exception("Ошибка в universal_handler при сохранении данных пользователя: %s", e)
        # опционально: можно тихо проигнорировать или сказать юзеру, что что-то не так
        if update.message:
            await update.message.reply_text("⚠️ Не удалось сохранить данные, попробуй ещё раз позже.")



# Ответ пользователю, если он пишет вне логики бота
async def handle_unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 Используйте кнопки или команды для работы с ботом:\n\n"
        "📝 Основные команды:\n"
        "/start - Начать работу с ботом\n"
        "/support - Связь с разработчиком\n"
        "/help - Справка\n\n"
        "Или используйте кнопки меню 🔽"
    )
    if update.message:
        await update.message.reply_text(help_text)

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
        # Если целей ещё нет — запускаем мастер пошагового ввода
        if update.message:
            # 👉 ВАЖНО: передаём именно update.message, а не весь update
            await start_goals_edit(update.message, context)
        return
    
    keyboard = [
        [KeyboardButton("📝 Добавить данные за сегодня"), KeyboardButton("📊 Цели и прогресс")],
        [KeyboardButton("📈 График изменения веса"), KeyboardButton("🏋️ История тренировок")],
        [KeyboardButton("📅 Серия и рекорды"), KeyboardButton("🏁 Начать новую тренировку")]
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=False
    )
    if update.message:
        await update.message.reply_text(
            "Привет! Я твой спортивный бот 💪\n"
            "Выбери действие ниже, воин:",
            reply_markup=reply_markup
        )

#Хендлер для получения file_id гифки
async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.animation:
        file_id = update.message.animation.file_id
        await update.message.reply_text(f"🎬 file_id гифки:\n{file_id}")
    else:
        await update.message.reply_text("❌ Это не гифка.")

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

async def edit_goals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск мастера изменения целей по кнопке '🎯 Цели'."""
    import logging
    try:
        if not update.callback_query:
            logging.error("edit_goals_callback вызван без callback_query")
            return

        user_id = str(update.callback_query.from_user.id)
        username = update.callback_query.from_user.username or "неизвестно"
        ensure_user_file_exists(user_id, username)

        query = update.callback_query
        await query.answer()

        # Запускаем пошаговый ввод целей
        await start_goals_edit(query, context)

    except Exception as e:
        logging.exception("Ошибка в edit_goals_callback: %s", e)
        # Если можем, отвечаем пользователю, чтобы не висела "часика"
        if update.callback_query:
            try:
                await update.callback_query.message.reply_text("⚠️ Не удалось начать редактирование целей. Попробуй ещё раз позже.")
            except Exception:
                pass


# Обработка произвольных текстов
async def route_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import logging
    print("📥 route_text_handler сработал!")

    try:
        if not update.message:
            print("⚠️ Нет update.message")
            return

        user_id = str(update.message.from_user.id)
        user_name = update.message.from_user.username or "неизвестно"

        from utils.data import ensure_user_file_exists

        ensure_user_file_exists(user_id, user_name)

        # Если запущен мастер изменения целей — обрабатываем ввод тут
        if context.user_data.get("goals_state"):
            await handle_goals_input(update, context)
            return

        if "текущая_тренировка" in context.user_data and "текущее_упражнение" in context.user_data:
            await сохранить_результат_упражнения(update, context)
            return

        if context.user_data.get("ожидаем_новое_упражнение"):
            текст = update.message.text.strip()
            muscle = context.user_data.get("выбранная_мышца")
            data = load_user_data(user_id)
            data.setdefault("доп_упражнения", {})
            data["доп_упражнения"].setdefault(muscle, []).append(текст)
            write_user_data(user_id, data)
            context.user_data.pop("ожидаем_новое_упражнение")
            await update.message.reply_text(f"✅ Упражнение «{текст}» добавлено в список на {muscle}!")
            await назад_к_мышцам_callback(update, context)
            return

        if "editing_field" in context.user_data:
            await save_new_value(update, context)
            return

        if ":" in update.message.text:
            from utils.data import save_user_data
            await save_user_data(update, context)
            return

        await handle_unknown_message(update, context)

    except Exception as e:
        logging.exception("Ошибка в route_text_handler: %s", e)
        if update.message:
            await update.message.reply_text("⚠️ Произошла ошибка при обработке сообщения. Попробуй ещё раз.")
        


def register_base_commands(app: Application):
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("card", show_card))
    app.add_handler(CommandHandler("graph", plot_weight_graph))
    app.add_handler(CommandHandler("download_everything", send_all_user_data))
    app.add_handler(CommandHandler("users_count", show_users_count))
    app.add_handler(CommandHandler("k", send_commands_file))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("support", support_command))
    app.add_handler(CommandHandler("thousand", thousand_handler))
    app.add_handler(CommandHandler("update", notify_users))
    app.add_handler(CommandHandler("online", notify_online))

    # Кнопки с текстом
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📝 Добавить данные за сегодня$"), start_sequential_input))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📅 Серия и рекорды$"), show_statistics))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📊 Цели и прогресс$"), show_card))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📈 График изменения веса$"), plot_weight_graph))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🏋️ История тренировок$"), show_workout_card))
    app.add_handler(MessageHandler(filters.ANIMATION, send_all_user_data))  

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("^🏁 Начать новую тренировку$"), start_custom_workout)],
        states={},
        fallbacks=[]
    )
    app.add_handler(conv_handler)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_text_handler))


    # Callback кнопки

    # Универсальный обработчик редактирования полей карточки (вес, шаги, сон, калории)
    app.add_handler(CallbackQueryHandler(edit_field_callback, pattern="^edit_field:"))

    # Остальные
    app.add_handler(CallbackQueryHandler(choose_muscle, pattern="^мышца_"))
    app.add_handler(CallbackQueryHandler(edit_card_callback, pattern="^edit_card_fields$"))
    app.add_handler(CallbackQueryHandler(edit_workout_callback, pattern="^edit_workout$"))
    app.add_handler(CallbackQueryHandler(добавить_упражнение_callback, pattern="^добавить_упражнение$"))
    app.add_handler(CallbackQueryHandler(удалить_упражнение_callback, pattern="^удалить_упражнение$"))
    app.add_handler(CallbackQueryHandler(обработать_удаление_упражнения, pattern="^удали_упр_"))
    app.add_handler(CallbackQueryHandler(назад_к_мышцам_callback, pattern="^назад_к_мышцам$"))
    app.add_handler(CallbackQueryHandler(choose_program, pattern="^программа_"))
    app.add_handler(CallbackQueryHandler(edit_goals_callback, pattern="^edit_goals$"))