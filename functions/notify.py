import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    CommandHandler,
)

from config import ADMIN_ID  # берём из .env / config.py

USERS_DIR = "users"


def _get_admin_id_set() -> set[str]:
    """
    Превращает ADMIN_ID из конфига в множество строковых id.
    Поддерживает варианты:
    - '123456789'
    - '123456789,987654321'
    - ' 123456789 , 987654321 '
    """
    if not ADMIN_ID:
        return set()

    raw = str(ADMIN_ID)
    parts = [p.strip() for p in raw.split(",")]
    return {p for p in parts if p}


def is_admin(update: Update) -> bool:
    """Проверяем, является ли пользователь админом."""
    user = update.effective_user
    if not user:
        return False

    user_id = str(user.id)
    admin_ids = _get_admin_id_set()
    return user_id in admin_ids


async def _require_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Проверяет права администратора.
    Возвращает True, если пользователь админ, иначе отправляет сообщение и False.
    """
    # нет вообще настроенного ADMIN_ID
    admin_ids = _get_admin_id_set()
    if not admin_ids:
        # стараемся не упасть, даже если нет message
        target = update.message or getattr(update, "effective_message", None)
        if target:
            await target.reply_text(
                "⚠️ ADMIN_ID не настроен.\n\n"
                "Добавь в файл .env строку, например:\n"
                f"ADMIN_ID={update.effective_user.id}"
            )
        logging.warning("Попытка использовать рассылку без настроенного ADMIN_ID")
        return False

    if not is_admin(update):
        user_id = update.effective_user.id if update.effective_user else "unknown"
        target = update.message or getattr(update, "effective_message", None)
        if target:
            await target.reply_text(
                "⛔ У тебя нет прав для этой команды.\n\n"
                f"Твой id: {user_id}\n"
                f"ADMIN_ID (из конфига): {', '.join(sorted(admin_ids))}"
            )
        logging.info("Пользователь %s пытался выполнить админ-команду", user_id)
        return False

    return True


async def broadcast_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message: str,
    header: str,
):
    """
    Универсальная рассылка по всем пользователям из папки users/.
    Работает только для администратора.
    """
    # 1) проверяем, что это админ
    if not await _require_admin(update, context):
        return

    # 2) проверяем, что папка users существует
    if not os.path.exists(USERS_DIR):
        target = update.message or getattr(update, "effective_message", None)
        if target:
            await target.reply_text(f"❌ Папка {USERS_DIR} не найдена.")
        logging.warning("Папка %s для рассылки не найдена", USERS_DIR)
        return

    success = 0
    failed = 0

    # 3) проходим по всем JSON-файлам в users/
    for filename in os.listdir(USERS_DIR):
        if not filename.endswith(".json"):
            continue

        chat_id = filename.removesuffix(".json")
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
            logging.info("✅ Отправлено пользователю %s", chat_id)
            success += 1
        except Exception as e:
            logging.warning("❌ Ошибка при отправке пользователю %s: %s", chat_id, e)
            failed += 1

    # 4) итоговое сообщение админу
    target = update.message or getattr(update, "effective_message", None)
    if target:
        await target.reply_text(
            f"{header}\n\n"
            f"Успешно: {success}\n"
            f"Ошибки: {failed}"
        )


# 🔔 Команда /update — уведомить о техработах
async def notify_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "⚠️ Бот временно недоступен.\n"
        "Идёт обновление. Вернёмся в течение 15 минут!"
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


def register_notify_handlers(app: Application):
    """Регистрируем команды рассылки в приложении."""
    app.add_handler(CommandHandler("update", notify_users))
    app.add_handler(CommandHandler("online", notify_online))
