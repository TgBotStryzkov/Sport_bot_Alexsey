from telegram import Update
from telegram.ext import ContextTypes
from utils.data import load_user_data
import os
import zipfile
import logging
from functions.notify import is_admin
from config import ADMIN_ID


# Отправляет архив со всеми данными пользователей администратору
async def send_all_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logging.error("send_all_user_data вызван без update.message")
        return

    # проверяем права через is_admin из notify.py
    if not is_admin(update):
        await update.message.reply_text("⛔ У тебя нет прав на эту команду.")
        return

    users_dir = "users"
    if not os.path.isdir(users_dir):
        await update.message.reply_text("⚠️ Папка с пользователями не найдена, нечего отправлять.")
        logging.warning("send_all_user_data: папка %s не найдена", users_dir)
        return
    
    archive_name = "all_users_data.zip"

    try:
        # создаём архив
        with zipfile.ZipFile(archive_name, "w") as zipf:
            files_found = False
            for root, dirs, files in os.walk(users_dir):
                for file in files:
                    files_found = True
                    filepath = os.path.join(root, file)
                    try:
                        zipf.write(filepath)
                    except Exception as e:
                        logging.warning("Не удалось добавить файл %s в архив: %s", filepath, e)

        if not files_found:
            await update.message.reply_text("⚠️ В папке пользователей нет файлов для отправки.")
            return

        # отправляем архив
        with open(archive_name, "rb") as f:
            await update.message.reply_document(document=f, filename=archive_name)

    except Exception as e:
        logging.exception("Ошибка при формировании/отправке архива пользователей: %s", e)
        try:
            await update.message.reply_text("⚠️ Не удалось сформировать и отправить архив.")
        except Exception:
            pass
    finally:
        # пытаемся удалить архив в любом случае
        if os.path.exists(archive_name):
            try:
                os.remove(archive_name)
            except Exception as e:
                logging.warning("Не удалось удалить временный архив %s: %s", archive_name, e)


# Показывает админу, сколько пользователей у бота
async def show_users_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logging.error("show_users_count вызван без update.message")
        return

    # Проверка, что это админ
    if not is_admin(update):
        await update.message.reply_text("⛔ У тебя нет прав на эту команду.")
        return

    try:
        users_dir = "users"
        if not os.path.isdir(users_dir):
            await update.message.reply_text("👤 Пользователей пока нет.")
            return

        count = sum(1 for name in os.listdir(users_dir) if name.endswith(".json"))
        await update.message.reply_text(f"👤 Количество пользователей бота: {count}")
    except Exception as e:
        logging.exception("Ошибка в show_users_count: %s", e)
        try:
            await update.message.reply_text("⚠️ Не удалось посчитать пользователей. Попробуй позже.")
        except Exception:
            pass


# Отправляет админу текстовый файл со списком команд
async def send_commands_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        logging.error("send_commands_file вызван без update.message")
        return

    # Только для админа
    if not is_admin(update):
        await update.message.reply_text("⛔ У тебя нет прав на эту команду.")
        return

    # Здесь ты сам можешь править список команд по мере надобности
    commands_text = (
        "/start - запуск бота\n"
        "/card - дневник, карточка\n"
        "/graph - график веса\n"
        "/download_everything - скачать все данные пользователей (админ)\n"
        "/users_count - количество пользователей (админ)\n"
        "/update - уведомить о техработах (админ)\n"
        "/online - уведомить что бот работает (админ)\n"
        "/help - помощь\n"
        "/support - отправить сообщение разрабу\n"
        "/thousand - похвала за 1000 строк кода в боте\n"
    )

    filename = "bot_commands.txt"

    try:
        # создаём файл
        with open(filename, "w", encoding="utf-8") as f:
            f.write(commands_text)

        # отправляем как документ
        with open(filename, "rb") as f:
            await update.message.reply_document(document=f, filename=filename)

    except Exception as e:
        logging.exception("Ошибка в send_commands_file: %s", e)
        try:
            await update.message.reply_text("⚠️ Не удалось отправить файл с командами.")
        except Exception:
            pass
    finally:
        # удаляем временный файл
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception as e:
                logging.warning("Не удалось удалить временный файл %s: %s", filename, e)
