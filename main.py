import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import sqlite3
from datetime import datetime
import calendar
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = '6232114231:AAEDTyOA4UiGeZyRT9zc9fT7HNCL0fkjt18'
ADMIN_CHAT_ID = 6649326029


def init_db():
    conn = sqlite3.connect('bookings.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bookings 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  room TEXT, 
                  company TEXT, 
                  date TEXT, 
                  time TEXT, 
                  event_name TEXT, 
                  status TEXT, 
                  user_id TEXT)''')  # Убедимся, что user_id есть в таблице
    conn.commit()
    conn.close()


def is_valid_time(time_str):
    try:
        start, end = time_str.split('-')
        start_hour, start_min = map(int, start.split(':'))
        end_hour, end_min = map(int, end.split(':'))
        start_time = start_hour * 60 + start_min
        end_time = end_hour * 60 + end_min
        if 7 * 60 <= start_time < end_time <= 22 * 60 and 0 <= start_min <= 59 and 0 <= end_min <= 59:
            return True
        return False
    except:
        return False


def is_time_available(room, date, time):
    try:
        with sqlite3.connect('bookings.db') as conn:
            c = conn.cursor()
            c.execute("SELECT time FROM bookings WHERE room=? AND date=? AND status='Занято'", (room, date))
            booked_times = c.fetchall()

        if not booked_times:
            return True

        new_start, new_end = time.split('-')
        new_start_hour, new_start_min = map(int, new_start.split(':'))
        new_end_hour, new_end_min = map(int, new_end.split(':'))
        new_start_minutes = new_start_hour * 60 + new_start_min
        new_end_minutes = new_end_hour * 60 + new_end_min

        for booked_time in booked_times:
            booked_start, booked_end = booked_time[0].split('-')
            booked_start_hour, booked_start_min = map(int, booked_start.split(':'))
            booked_end_hour, booked_end_min = map(int, booked_end.split(':'))
            booked_start_minutes = booked_start_hour * 60 + booked_start_min
            booked_end_minutes = booked_end_hour * 60 + booked_end_min

            if not (new_end_minutes <= booked_start_minutes or new_start_minutes >= booked_end_minutes):
                return False
        return True
    except sqlite3.Error as e:
        logger.error(f"Ошибка при работе с базой данных: {e}")
        return False


def generate_calendar(year, month):
    cal = calendar.monthcalendar(year, month)
    keyboard = []
    for week in cal:
        week_buttons = []
        for day in week:
            if day == 0:
                week_buttons.append(InlineKeyboardButton(" ", callback_data='noop'))
            else:
                date_str = f"{day:02d}.{month:02d}.{year}"
                week_buttons.append(InlineKeyboardButton(str(day), callback_data=f"date_{date_str}"))
        keyboard.append(week_buttons)

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    month_names = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                   "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    keyboard.append([
        InlineKeyboardButton(f"<-- {month_names[prev_month - 1]}", callback_data=f"month_{prev_year}_{prev_month}"),
        InlineKeyboardButton(f"{month_names[next_month - 1]} -->", callback_data=f"month_{next_year}_{next_month}")
    ])
    return InlineKeyboardMarkup(keyboard)


def get_back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data='back')]])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("Забронировать переговорную", callback_data='book')],
        [InlineKeyboardButton("Посмотреть график", callback_data='schedule')],
        [InlineKeyboardButton("Отменить бронь", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Добро пожаловать в бот бронирования переговорных БТГ+, пожалуйста выберите необходимую функцию. Если по каким то причинам бот не работает отправьте в бот команду "\\start" для перезапуска.',
        reply_markup=reply_markup
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'book':
        keyboard = [
            [InlineKeyboardButton("Большая переговорная (21 каб)", callback_data='room_big')],
            [InlineKeyboardButton("Маленькая переговорная (7 каб)", callback_data='room_small')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('Выберите переговорную:', reply_markup=reply_markup)
    elif query.data == 'schedule':
        year, month = datetime.now().year, datetime.now().month
        reply_markup = generate_calendar(year, month)
        await query.edit_message_text('Выберите дату для графика:', reply_markup=reply_markup)
        context.user_data['state'] = 'schedule_date'
    elif query.data == 'cancel':
        year, month = datetime.now().year, datetime.now().month
        reply_markup = generate_calendar(year, month)
        await query.edit_message_text('Выберите дату для отмены брони:', reply_markup=reply_markup)
        context.user_data['state'] = 'cancel_date'
    elif query.data.startswith('room_'):
        room = 'Большая' if query.data == 'room_big' else 'Маленькая'
        context.user_data['room'] = room
        keyboard = [
            [InlineKeyboardButton("БТГ+", callback_data='company_btg')],
            [InlineKeyboardButton("Другая", callback_data='company_other')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('Выберите компанию:', reply_markup=reply_markup)
    elif query.data.startswith('company_'):
        company = 'БТГ+' if query.data == 'company_btg' else 'Другая'
        context.user_data['company'] = company
        year, month = datetime.now().year, datetime.now().month
        reply_markup = generate_calendar(year, month)
        await query.edit_message_text('Выберите дату бронирования:', reply_markup=reply_markup)
        context.user_data['state'] = 'book_date'
    elif query.data.startswith('month_'):
        _, year, month = query.data.split('_')
        year, month = int(year), int(month)
        reply_markup = generate_calendar(year, month)
        state = context.user_data.get('state')
        new_text = ''
        if state == 'book_date':
            new_text = 'Выберите дату бронирования:'
        elif state == 'schedule_date':
            new_text = 'Выберите дату для графика:'
        elif state == 'cancel_date':
            new_text = 'Выберите дату для отмены брони:'

        current_text = query.message.text
        current_markup = str(query.message.reply_markup)
        if new_text != current_text or str(reply_markup) != current_markup:
            await query.edit_message_text(new_text, reply_markup=reply_markup)
    elif query.data.startswith('date_'):
        date = query.data.split('_')[1]
        state = context.user_data.get('state')
        if state == 'book_date':
            context.user_data['date'] = date
            with sqlite3.connect('bookings.db') as conn:
                c = conn.cursor()
                c.execute("SELECT time, company FROM bookings WHERE room=? AND date=? AND status='Занято'",
                          (context.user_data['room'], date))
                bookings = c.fetchall()
            booking_list = '\n'.join([f"{t[0]} {t[1]}" for t in bookings]) if bookings else 'Свободно весь день.'
            await query.message.reply_text(
                f"Занятость {context.user_data['room']} на {date}:\n{booking_list}\n\nВведите время (например, 8:00-9:00 или 9:20-9:50):",
                reply_markup=get_back_button()
            )
            context.user_data['state'] = 'book_time'
        elif state == 'schedule_date':
            await show_schedule(update, context, date)
            context.user_data.clear()
        elif state == 'cancel_date':
            context.user_data['date'] = date
            with sqlite3.connect('bookings.db') as conn:
                c = conn.cursor()
                c.execute("SELECT id, time FROM bookings WHERE date=? AND status='Занято'", (date,))
                bookings = c.fetchall()
            if not bookings:
                await query.edit_message_text(f"На {date} нет броней для отмены.", reply_markup=get_back_button())
                return
            keyboard = [[InlineKeyboardButton(f"{b[1]}", callback_data=f"cancel_time_{b[0]}")] for b in bookings]
            keyboard.append([InlineKeyboardButton("Назад", callback_data='back')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"Выберите время для отмены на {date}:", reply_markup=reply_markup)
            context.user_data['state'] = 'cancel_time'
    elif query.data.startswith('cancel_time_'):
        booking_id = query.data.split('_')[2]
        with sqlite3.connect('bookings.db') as conn:
            c = conn.cursor()
            c.execute("SELECT room, company, date, time, event_name, user_id FROM bookings WHERE id=?", (booking_id,))
            booking = c.fetchone()
        context.user_data['cancel_booking_id'] = booking_id
        # Сохраняем user_id из базы, чтобы использовать его позже
        context.user_data['user_id'] = booking[5] if booking[5] else query.from_user.id
        keyboard = [
            [InlineKeyboardButton("Подтвердить", callback_data=f"confirm_cancel_{booking_id}"),
             InlineKeyboardButton("Отклонить", callback_data=f"reject_cancel_{booking_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"Запрос на отмену брони:\nПереговорная: {booking[0]}\nКомпания: {booking[1]}\nДата: {booking[2]}\nВремя: {booking[3]}\nМероприятие: {booking[4]}\nОт пользователя: @{query.from_user.username}",
                reply_markup=reply_markup
            )
            await query.edit_message_text("Запрос на отмену отправлен администратору. Ожидай подтверждения.",
                                          reply_markup=get_back_button())
            context.user_data['state'] = 'awaiting_cancel'
        except telegram.error.TelegramError as e:
            logger.error(f"Не удалось отправить запрос администратору: {e}")
            await query.edit_message_text(
                f"Не удалось отправить запрос администратору: {str(e)}. Пожалуйста, попробуй позже.",
                reply_markup=get_back_button())
            context.user_data.clear()
    elif query.data.startswith('confirm_cancel_'):
        booking_id = query.data.split('_')[2]
        # Получаем user_id из базы, а не из context.user_data
        with sqlite3.connect('bookings.db') as conn:
            c = conn.cursor()
            c.execute("SELECT user_id FROM bookings WHERE id=?", (booking_id,))
            booking = c.fetchone()
            c.execute("UPDATE bookings SET status='Отменено' WHERE id=?", (booking_id,))
            conn.commit()

        user_id = booking[0] if booking else None
        if user_id:
            try:
                logger.info(f"Отправляю уведомление пользователю с chat_id: {user_id}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text="Ваша бронь успешно отменена администратором.",
                    reply_markup=get_back_button()
                )
                logger.info("Уведомление пользователю успешно отправлено")
            except telegram.error.TelegramError as e:
                logger.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
        else:
            logger.error(f"Не удалось найти user_id для брони с id {booking_id}")

        try:
            await query.edit_message_text("Бронь успешно отменена.", reply_markup=get_back_button())
        except telegram.error.TelegramError as e:
            logger.error(f"Не удалось обновить сообщение для админа: {e}")
        context.user_data.clear()
    elif query.data.startswith('reject_cancel_'):
        booking_id = query.data.split('_')[2]
        # Получаем user_id из базы
        with sqlite3.connect('bookings.db') as conn:
            c = conn.cursor()
            c.execute("SELECT user_id FROM bookings WHERE id=?", (booking_id,))
            booking = c.fetchone()

        user_id = booking[0] if booking else None
        if user_id:
            try:
                logger.info(f"Отправляю уведомление пользователю с chat_id: {user_id}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text="Отмена бронирования отклонена администратором.",
                    reply_markup=get_back_button()
                )
                logger.info("Уведомление пользователю успешно отправлено")
            except telegram.error.TelegramError as e:
                logger.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
        else:
            logger.error(f"Не удалось найти user_id для брони с id {booking_id}")

        try:
            await query.edit_message_text("Отмена отклонена.", reply_markup=get_back_button())
        except telegram.error.TelegramError as e:
            logger.error(f"Не удалось обновить сообщение для админа: {e}")
        context.user_data.clear()
    elif query.data == 'back':
        context.user_data.clear()
        keyboard = [
            [InlineKeyboardButton("Забронировать переговорную", callback_data='book')],
            [InlineKeyboardButton("Посмотреть график", callback_data='schedule')],
            [InlineKeyboardButton("Отменить бронь", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            'Добро пожаловать в бот бронирования переговорных БТГ+, пожалуйста выберите необходимую функцию. Если по каким то причинам бот не работает отправьте в бот команду "\\start" для перезапуска.',
            reply_markup=reply_markup
        )
    elif query.data == 'noop':
        pass


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    state = context.user_data.get('state')

    logger.info(f"Получено сообщение: {text}, состояние: {state}")

    if state == 'book_time':
        logger.info("Проверяю время...")
        if is_valid_time(text):
            logger.info("Время валидно, проверяю доступность...")
            if is_time_available(context.user_data['room'], context.user_data['date'], text):
                logger.info("Время свободно, перехожу к вводу названия мероприятия")
                context.user_data['time'] = text
                await update.message.reply_text('Введите название мероприятия:', reply_markup=get_back_button())
                context.user_data['state'] = 'book_event'
            else:
                logger.info("Время занято")
                await update.message.reply_text('Это время уже занято! Выберите другое:',
                                                reply_markup=get_back_button())
        else:
            logger.info("Неверный формат времени")
            await update.message.reply_text(
                'Неверный формат или время вне графика (7:00-22:00)! Введи, например, 8:00-9:00 или 9:20-9:50:',
                reply_markup=get_back_button())
    elif state == 'book_event':
        logger.info("Сохраняю мероприятие...")
        event_name = text
        try:
            with sqlite3.connect('bookings.db') as conn:
                c = conn.cursor()
                c.execute(
                    "INSERT INTO bookings (room, company, date, time, event_name, status, user_id) VALUES (?, ?, ?, ?, ?, 'Занято', ?)",
                    (context.user_data['room'], context.user_data['company'], context.user_data['date'],
                     context.user_data['time'], event_name, str(update.message.from_user.id)))
                conn.commit()
            keyboard = [
                [InlineKeyboardButton("Назад", callback_data='back')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"Бронь подтверждена!\nПереговорная: {context.user_data['room']}\nДата: {context.user_data['date']}\nВремя: {context.user_data['time']}\nМероприятие: {event_name}",
                reply_markup=reply_markup
            )
            context.user_data.clear()
        except sqlite3.Error as e:
            logger.error(f"Ошибка при сохранении брони: {e}")
            await update.message.reply_text(
                "Произошла ошибка при сохранении брони. Попробуй еще раз.",
                reply_markup=get_back_button()
            )


async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE, date):
    with sqlite3.connect('bookings.db') as conn:
        c = conn.cursor()
        c.execute(
            "SELECT time, company, event_name, status FROM bookings WHERE room='Большая' AND date=? AND status='Занято'",
            (date,))
        big_room_bookings = c.fetchall()
        c.execute(
            "SELECT time, company, event_name, status FROM bookings WHERE room='Маленькая' AND date=? AND status='Занято'",
            (date,))
        small_room_bookings = c.fetchall()

    message = f"График на {date}:\n\n"
    message += "Большая переговорная:\n"
    if not big_room_bookings:
        message += "Нет броней.\n"
    else:
        for booking in big_room_bookings:
            message += f"{booking[0]} {booking[1]} - {booking[2]}\n"
    message += "\n"
    message += "Маленькая переговорная:\n"
    if not small_room_bookings:
        message += "Нет броней.\n"
    else:
        for booking in small_room_bookings:
            message += f"{booking[0]} {booking[1]} - {booking[2]}\n"

    await update.callback_query.edit_message_text(message, reply_markup=get_back_button())


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Произошла ошибка: {context.error}")
    if isinstance(context.error, telegram.error.Conflict):
        logger.error("Конфликт: другой экземпляр бота уже работает. Останавливаю этот экземпляр.")
        raise SystemExit
    elif isinstance(context.error, telegram.error.TimedOut):
        logger.error("Ошибка: Timed out. Продолжаю ожидать...")


def main():
    init_db()
    application = Application.builder().token(TOKEN).read_timeout(60).write_timeout(60).connect_timeout(
        60).get_updates_read_timeout(60).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES, timeout=60)


if __name__ == '__main__':
    main()