import os
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    CommandHandler,
)

from config import ADMIN_ID  # ADMIN_ID у нас строка из .env


# 📤 Универсальная функция рассылки с проверкой прав администратора
async def broadcast_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message: str,
    header: str,
):
    user_id = str(update.effective_user.id)

    # 1) Если ADMIN_ID вообще не настроен
    if not ADMIN_ID:
        await update.message.reply_text(
            "⚠️ ADMIN_ID не настроен.\n"
            "Добавь в файл .env строку:\n\n"
            f"ADMIN_ID={user_id}"
        )
        return

    # 2) Проверка, что команду вызывает именно админ
    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ У тебя нет прав для этой команды.\n\n"
            f"Твой id: {user_id}\n"
            f"ADMIN_ID из конфига: {ADMIN_ID}"
        )
        return

    # 3) Собираем список пользователей по файлам в папке users
    users_dir = "users"
    if not os.path.exists(users_dir):
        await update.message.reply_text("❌ Папка users не найдена.")
        return

    success = 0
    failed = 0

    for filename in os.listdir(users_dir):
        if not filename.endswith(".json"):
            continue

        chat_id = filename.replace(".json", "")
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
            print(f"✅ Отправлено пользователю {chat_id}")
            success += 1
        except Exception as e:
            print(f"❌ Ошибка при отправке пользователю {chat_id}: {e}")
            failed += 1

    await update.message.reply_text(
        f"{header}\n\nУспешно: {success}\nОшибки: {failed}"
    )


# 🔔 Команда /update — уведомить о техработах
async def notify_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "⚠️ Бот временно недоступен. "
        "Мы выкатываем обновление. Вернёмся в течение 15 минут!"
    )
    await broadcast_message(
        update,
        context,
        message,
        "✅ Рассылка о техработах завершена.",
    )


# 🔔 Команда /online — уведомить, что бот снова работает
async def notify_online(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = "✅ Бот снова работает. Спасибо за ожидание!"
    await broadcast_message(
        update,
        context,
        message,
        "📣 Уведомление отправлено.",
    )


# 🔧 Регистрация обработчиков
def register_notify_handlers(app: Application):
    app.add_handler(CommandHandler("update", notify_users))
    app.add_handler(CommandHandler("online", notify_online))
