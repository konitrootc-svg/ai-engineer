import logging
import os

from dotenv import load_dotenv

load_dotenv()

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import ai

logging.basicConfig(level=logging.INFO)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "សួស្តី! ខ្ញុំជា AI Engineer។ សួរអ្វីក៏បាន។\n"
        "/reset ដើម្បីចាប់ផ្តើមការសន្ទនាថ្មី។"
    )


async def reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ai.reset(update.effective_user.id)
    await update.message.reply_text("បានចាប់ផ្តើមថ្មី។")


async def chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        answer = await ai.ask(update.effective_user.id, update.message.text)
    except Exception:
        logging.exception("AI error")
        await update.message.reply_text("មានបញ្ហា សូមព្យាយាមម្តងទៀត។")
        return
    for i in range(0, len(answer), 4000):
        await update.message.reply_text(answer[i : i + 4000])


def main():
    app = ApplicationBuilder().token(os.environ["BOT_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.run_polling()


if __name__ == "__main__":
    main()
