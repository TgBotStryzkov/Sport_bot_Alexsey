from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes
import logging

from .core import (
    choose_program,
    choose_muscle,
    начать_упражнения_callback,
    добавить_упражнение_callback,
    удалить_упражнение_callback,
    обработать_удаление_упражнения,
    назад_к_мышцам_callback,
    handle_exercise_button,
    handle_exercise_click,
)

from .card import (
    universal_handler,
    show_card,
    plot_weight_graph,
    show_statistics,
    edit_card_callback,
    edit_workout_callback,
)

async def safe_show_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await show_card(update, context)
    except Exception as e:
        logging.exception("Ошибка при выполнении команды /card: %s", e)
        await update.message.reply_text("⚠️ Не удалось выполнить команду. Попробуй позже.")

async def safe_show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await show_statistics(update, context)
    except Exception as e:
        logging.exception("Ошибка при выполнении команды /stats: %s", e)
        await update.message.reply_text("⚠️ Не удалось выполнить команду. Попробуй позже.")

async def safe_plot_weight_graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await plot_weight_graph(update, context)
    except Exception as e:
        logging.exception("Ошибка при выполнении команды /weight_graph: %s", e)
        await update.message.reply_text("⚠️ Не удалось выполнить команду. Попробуй позже.")

async def safe_universal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await universal_handler(update, context)
    except Exception as e:
        logging.exception("Ошибка при обработке текста: %s", e)
        await update.message.reply_text("⚠️ Ошибка в данных. Попробуй снова.")        

def register_training_handlers(app: Application):
    # 🔸 Команды
    app.add_handler(CommandHandler("card", safe_show_card))
    app.add_handler(CommandHandler("stats", safe_show_statistics))
    app.add_handler(CommandHandler("weight_graph", safe_plot_weight_graph))

    # 🔸 Кнопки и действия
    app.add_handler(CallbackQueryHandler(choose_program, pattern="^программа_"))
    app.add_handler(CallbackQueryHandler(choose_muscle, pattern="^мышца_"))
    app.add_handler(CallbackQueryHandler(начать_упражнения_callback, pattern="^начать_упражнения$"))
    app.add_handler(CallbackQueryHandler(добавить_упражнение_callback, pattern="^добавить_упражнение$"))
    app.add_handler(CallbackQueryHandler(удалить_упражнение_callback, pattern="^удалить_упражнение$"))
    app.add_handler(CallbackQueryHandler(обработать_удаление_упражнения, pattern="^удали_упр_"))
    app.add_handler(CallbackQueryHandler(назад_к_мышцам_callback, pattern="^назад_к_мышцам$"))
    app.add_handler(CallbackQueryHandler(handle_exercise_click, pattern="^упр_"))

    

    # 🔸 Редактирование карточки
    app.add_handler(CallbackQueryHandler(edit_card_callback, pattern="^edit_card_fields$"))
    app.add_handler(CallbackQueryHandler(edit_workout_callback, pattern="^edit_workout$"))
    app.add_handler(CallbackQueryHandler(handle_exercise_button, pattern="^handle_exercise_button$"))

    # 🔸 Последовательный ввод и сохранение данных
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, safe_universal_handler))

