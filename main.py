import datetime
import random

from dotenv import load_dotenv
from os import getenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes


load_dotenv()
TOKEN = getenv("TOKEN")
MANAGERS_ID = getenv("MANAGERS_ID")

async def create_random_integer():
    return random.randrange(0, 100000000000000)


def parse_text(text):
    """Функция разбивает сообщение на:
    tel_id - id сотрудника, которому надо отправить напоминание
    text - сообщение, предназначенное сотруднику
    date - дату отправки сообщения
    time - время отправки сообщения
    time_to_respond - время, данное сотруднику на ответ\
    """
    parsed_text = text.split('\n')
    return parsed_text


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="WRONG COMMAND")


async def send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job

    keyboard = [
        [
            InlineKeyboardButton("Выполнено", callback_data=f"Выполнено {job.name}"),
            InlineKeyboardButton("Не сделано", callback_data=f"Не сделано {job.name}"),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(job.chat_id, text=f"{job.data}", reply_markup=reply_markup)


async def setup_timer(context: ContextTypes.DEFAULT_TYPE) -> None:

    job = context.job

    await context.bot.send_message(job.chat_id, text=f"{job.data}")


async def get_users_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.startswith("Выполнено") or update.message.text.startswith("Не сделано"):
        return

    await context.bot.send_message(MANAGERS_ID, text=f"{update.message.text}")

    job_name = update.message.text.split()[1]

    jobs = context.job_queue.get_jobs_by_name(job_name+"_ignored")
    for job in jobs:
        job.schedule_removal()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    managers_id = update.effective_chat.id

    if MANAGERS_ID != managers_id:
        await get_users_response(update, context)
        return 

    await context.bot.send_message(chat_id=managers_id, text='Запрос получен, ожидайте.')

    data = parse_text(update.message.text)

    time_to_respond = data.pop()
    time = data.pop()
    date = data.pop()
    text = data.pop()
    worker_id = data.pop()

    due_date = datetime.datetime.strptime(f'{time}:00 {date}', format="%a %b %d %H:%M:%S %Y")
    seconds_left = due_date - datetime.datetime.now()

    try:
        due = float(seconds_left)
        if due < 0:
            await update.effective_message.reply_text("Невозможно отправить сообщение в прошлое.")
            return

        job_name = await create_random_integer()

        context.job_queue.run_once(send_reminder, due, chat_id=worker_id, name=job_name, data=text)
        context.job_queue.run_once(setup_timer, time_to_respond, chat_id=managers_id, name=job_name + '_ignored', data='Проигнорировано')

        text = "Время установлено."
        await update.effective_message.reply_text(text)

    except Exception:
        await update.effective_message.reply_text("Плохой запрос")



def main():
    application = ApplicationBuilder().token(TOKEN).build()
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    unknown_handler = MessageHandler(filters.COMMAND, unknown)

    application.add_handler(message_handler)
    application.add_handler(unknown_handler)

    application.run_polling()


if __name__ == '__main__':
    main()
