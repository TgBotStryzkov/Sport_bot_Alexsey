import logging
import warnings
warnings.filterwarnings("ignore", message=r"If 'per_message' is set", category=UserWarning)


from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes

from config import TOKEN
from functions.base import register_base_commands
from functions.training.register import register_training_handlers
from functions.notify import register_notify_handlers

from config import ADMIN_ID

# приведение ADMIN_ID к int (или None, если не задан/битый)
try:
    ADMIN_ID_INT = int(ADMIN_ID) if ADMIN_ID not in (None, "", "0") else None
except (TypeError, ValueError):
    ADMIN_ID_INT = None

from telegram.constants import ParseMode

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.bot").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)

async def notify_admin(context: ContextTypes.DEFAULT_TYPE, html_text: str) -> None:
    if ADMIN_ID_INT is None:
        return  # админ не настроен — выходим тихо
    try:
        await context.bot.send_message(chat_id=ADMIN_ID_INT, text=html_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error("Не удалось отправить сообщение админу: %s", e)


# ✅ Обработчик ошибок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error("Произошла ошибка:", exc_info=context.error)

    # Сообщение пользователю
    try:
        if update and isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text("❗ Произошла ошибка. Пожалуйста, попробуй позже.")
    except Exception as e:
        logging.error(f"Ошибка при отправке уведомления пользователю: {e}")

    # Отправка админу (HTML + усечённый traceback)
    try:
        import traceback, html
        tb = "".join(traceback.format_exception(None, context.error, context.error.__traceback__))
        # Чтобы не превысить лимит 4096 символов в Telegram:
        tb_short = tb[-3500:] if len(tb) > 3500 else tb

        message = (
            "⚠️ <b>Произошла ошибка</b>\n\n"
            f"<b>Ошибка:</b>\n<pre>{html.escape(str(context.error))}</pre>\n"
            f"<b>Traceback:</b>\n<pre>{html.escape(tb_short)}</pre>"
        )
        await notify_admin(context, message)
    except Exception as e:
        logging.error(f"Не удалось подготовить/отправить сообщение админу: {e}")



def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN пуст. Укажи его в .env как BOT_TOKEN=...")
    
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_error_handler(error_handler)  # ✅ Регистрируем обработчик ошибок

    register_base_commands(app)
    register_notify_handlers(app)
    register_training_handlers(app)

    print("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
