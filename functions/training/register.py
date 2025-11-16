from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from functions.base import route_text_handler

from .core import (
    choose_program,
    choose_muscle,
    начать_упражнения_callback,
    показать_следующее_упражнение,
    сохранить_результат_упражнения,
    добавить_упражнение_callback,
    удалить_упражнение_callback,
    обработать_удаление_упражнения,
    назад_к_мышцам_callback,
    handle_exercise_button,
    handle_exercise_click,
    receive_exercise_count
)

from .card import (
    universal_handler,
    show_card,
    plot_weight_graph,
    show_statistics,
    show_workout_card,
    edit_card_callback,
    edit_workout_callback,
    save_new_value,
)



def register_training_handlers(app: Application):
    # 🔸 Команды
    app.add_handler(CommandHandler("card", show_card))
    app.add_handler(CommandHandler("stats", show_statistics))
    app.add_handler(CommandHandler("weight_graph", plot_weight_graph))
    app.add_handler(CommandHandler("workout_plan", show_workout_card))

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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, universal_handler))

