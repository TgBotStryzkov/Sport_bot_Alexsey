# functions/send.py
from telegram import Update
from telegram.ext import ContextTypes
from utils.data import load_user_data
import json 
import os
import zipfile
from config import ADMIN_ID


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