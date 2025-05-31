from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import psycopg2
from datetime import datetime, timedelta
import logging
import os

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# API-токен бота из переменной окружения или значения по умолчанию
TOKEN = os.environ.get('TOKEN', '7991006616:AAEuHwhqbFyMVXTVy56ocv22JWZELf5kM7o')

# Telegram ID администратора
ADMIN_IDS = ['277399219'] # Должен быть список, даже с одним ID
# Названия уроков (ОБНОВЛЕНО согласно списку папок пользователя)
LESSON_TITLES = [
    "1 сабақ Орталық Азия және Ұлы Дала",
    "2 сабақ Қазақстан  территориясындағы тас ,қола және темір дәуірлері",
    "3 сабақ. Қазақстан территориясындағы алғашқы тайпалық одақтар мен ертедегі мемлекеттер",
    "4 сабақ. Ерте орта ғасырлардағы Қазақстан  тарихы",
    "5 сабақ. VI-IX ғасырлардағы Қазақстан  мәдениеті",
    "6 сабақ. Дамыған орта ғасырлар мемлекеттерінің тарихы",
    "7 сабақ. IX-XIII ғасырлардағы Қазақстан  мәдениеті",
    "8 сабақ. Кейінгі орта ғасырлар тарихы.(XIII-XVII ғасырлар)",
    "9 сабақ. XIII-XV ғасырдың бірінші жартысындағы мемлекеттердің саяси құрылымы, экономикасы және мәдениеті",
    "10 сабақ. Біртұтас Қазақ мемлекетінің құрылуы",
    "11 сабақ.XV-XVII ғасырлардағы Қазақ хандығының әлеуметтік-экономикалық дамуы және мәдениеті",
    "12 сабақ. Қазақ - жоңғар соғыстары",
    "13 сабақ. XVIII ғасырдағы Қазақ хандығы",
    "14 сабақ. XVIII ғасырдағы Қазақстан  мәдениеті",
    "15 сабақ. Отарлау және ұлт-азаттық күрес",
    "16 сабақ. Қазақстан Ресей империясының құрамында",
    "17 сабақ. Қазақстанның XIX-XX ғасыр басындағы мәдениеті",
    "18 сабақ. XX ғасырдың басындағы Қазақстан",
    "19 сабақ. Қазақстанда Кеңес билігінің орнауы",
    "20 сабақ. Қазақстан  тоталитарлық жүйе кезеңінде",
    "21 сабақ. Кеңестік Қазақстанның мәдениеті (1920-1930 жылдар)",
    "22 сабақ. Қазақстан Ұлы Отан соғысы жылдарында.(1941-1945 жылдар)",
    "23 сабақ. Қазақстан соғыстан кейінгі жылдарда (1946-1953 жылдар)",
    "24 сабақ. Қазақстан жылымық кезеңінде .(1954-1964 жылдар)",
    "25 сабақ. Қазақстан тоқырау кезеңінде. (1965-1985 жылдар)",
    "26 сабақ. Кеңестік Қазақстан мәдениеті. (1946-1985 жылдар)",
    "27 сабақ. Қазақстан қайта құру кезеңінде. (1986 - 1991 жылдар)",
    "28 сабақ. Қазақстан мемлекеттілігінің қайта жаңғыруы . (1991- 1996 жылдар)",
    "29 сабақ. Қазақстан Республикасының дамуы. (1997 жылдан бастап қазіргі күнге дейін)",
    "30 сабақ. Қазіргі заманғы Қазақстан мәдениеті"
]

# Подключение к PostgreSQL с использованием переменных окружения
conn = psycopg2.connect(
    dbname=os.environ.get('DB_NAME', 'bot'),
    user=os.environ.get('DB_USER', 'postgres'),
    password=os.environ.get('DB_PASSWORD', 'admin'),
    host=os.environ.get('DB_HOST', 'localhost'),
    port=os.environ.get('DB_PORT', '5432')
)
cur = conn.cursor()

# Добавляю глобальную переменную для хранения file_id видео после первой отправки
VIDEO_FILE_ID = None

# Функция для загрузки file_id из базы данных
def load_video_file_id():
    global VIDEO_FILE_ID
    try:
        # Проверяем, есть ли таблица для хранения настроек
        cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'settings')")
        table_exists = cur.fetchone()[0]
        
        if not table_exists:
            # Создаем таблицу, если она не существует
            cur.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
            conn.commit()
            logger.info("Created settings table")
        
        # Получаем file_id из базы данных
        cur.execute("SELECT value FROM settings WHERE key = 'video_file_id'")
        result = cur.fetchone()
        
        if result:
            VIDEO_FILE_ID = result[0]
            logger.info(f"Loaded video file_id from database: {VIDEO_FILE_ID}")
    except Exception as e:
        logger.error(f"Error loading video file_id from database: {e}")
        conn.rollback()

# Функция для сохранения file_id в базу данных
def save_video_file_id(file_id):
    try:
        cur.execute(
            "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = %s",
            ('video_file_id', file_id, file_id)
        )
        conn.commit()
        logger.info(f"Saved video file_id to database: {file_id}")
    except Exception as e:
        logger.error(f"Error saving video file_id to database: {e}")
        conn.rollback()

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Далее", callback_data='next')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "\"Тарихшы Нұрсұлтан\" Telegram каналына қош келдіңіз! 📚",
        reply_markup=reply_markup,
        protect_content=True
    )

# Обработчик кнопки "Далее"
async def next_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    logger.info(f"Next_step handler called with query.data: {query.data}")
    await query.answer()
    
    # Отправляем фотографию
    try:
        with open('photo.png', 'rb') as photo_file:
            await context.bot.send_photo(
                chat_id=query.from_user.id,
                photo=photo_file,
                protect_content=True
            )
    except FileNotFoundError:
        logger.error("Photo file not found: photo.png")
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="Фото файлы табылмады. Әкімшіге хабарласыңыз.",
            protect_content=True
        )
    except Exception as e:
        logger.error(f"Error sending photo in next_step handler: {e}")
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="Фотоны жіберу кезінде қате орын алды.",
            protect_content=True
        )
    
    # Сразу отправляем текст об авторе с кнопкой "Старт"
    keyboard = [[InlineKeyboardButton("Старт", callback_data='start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text="Тәжен Нұрсұлтан Шәутенұлы\n"
             "Қырық жылға жуық еңбек өтілі бар Педагог-шебер, ҚР \"Білім беру ісінің үздігі\", "
             "\"Ы. Алтынсарин төсбелгісінің\" иегері, Қазақстан тарихы пәні бойынша "
             "бірнеше әдістемелік құралдардың авторы.",
        reply_markup=reply_markup,
        protect_content=True
    )

# Обработчик кнопки "Старт"
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    logger.info(f"Button handler called with query.data: {query.data}")
    await query.answer()
    if query.data == 'start':
        keyboard = [[InlineKeyboardButton("Сабақтарға қол жеткізгім келеді!", callback_data='get_access')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        global VIDEO_FILE_ID
        video_path = 'video.mp4'  # Путь к вашему видео файлу

        try:
            # Если у нас уже есть file_id от предыдущей отправки, используем его
            if VIDEO_FILE_ID:
                logger.info(f"Using cached video file_id: {VIDEO_FILE_ID}")
                await context.bot.send_video(
                    chat_id=query.from_user.id,
                    video=VIDEO_FILE_ID,
                    caption=None,  # Без подписи
                    reply_markup=reply_markup,
                    read_timeout=120,  # Увеличенный таймаут
                    write_timeout=120,  # Увеличенный таймаут
                    connect_timeout=120,  # Увеличенный таймаут
                    protect_content=True
                )
            else:
                # Отправляем видео с диска и сохраняем file_id для будущего использования
                with open(video_path, 'rb') as video_file:
                    message = await context.bot.send_video(
                        chat_id=query.from_user.id,
                        video=video_file,
                        caption=None,  # Без подписи
                        reply_markup=reply_markup,
                        read_timeout=120,  # Увеличенный таймаут
                        write_timeout=120,  # Увеличенный таймаут
                        connect_timeout=120,  # Увеличенный таймаут
                        protect_content=True
                    )
                    # Сохраняем file_id для будущего использования
                    VIDEO_FILE_ID = message.video.file_id
                    logger.info(f"Saved video file_id: {VIDEO_FILE_ID}")
                    # Сохраняем file_id в базу данных
                    save_video_file_id(VIDEO_FILE_ID)
        except FileNotFoundError:
            logger.error(f"Video file not found: {video_path}")
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text="Видео файлы табылмады. Әкімшіге хабарласыңыз.",
                reply_markup=reply_markup,
                protect_content=True
            )
        except Exception as e:
            logger.error(f"Error sending video in button handler: {e}")
            # В случае ошибки при отправке видео, попробуем альтернативный подход
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text="Видеоны жіберу кезінде қате орын алды. Сізге бәрібір жалғастыруға мүмкіндік береміз.",
                reply_markup=reply_markup,
                protect_content=True
            )

# Обработчик кнопки "Сабақтарға қол жеткізгім келеді!"
async def get_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    logger.info(f"Get_access handler called with query.data: {query.data}")
    await query.answer()
    if query.data == 'get_access':
        # Кнопка для оплаты через Kaspi Pay
        keyboard = [[InlineKeyboardButton("Төлем жасау", url='https://pay.kaspi.kz/pay/2tyi0ezv')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.reply_text(
            "💰 Курс туралы ақпарат:\n\n"
            "Аудио сабақтарды пайдалану мерзімі - 3 ай.\n"
            "Бағасы - 48 000 теңге.\n"
            "Осы төлемді төлеп, каналға қосылыңыз.\n\n"
            "Каналға қосылу сізге 3 ай бойы Тәжен Нұрсұлтанның Қазақстан тарихы пәнінен "
            "124 тақырыпты қамтитын авторлық аудио сабақтарын тыңдауға мүмкіндік береді!",
            reply_markup=reply_markup,
            protect_content=True
        )
        # Сообщение сразу после нажатия кнопки
        await query.message.reply_text(
            "Чекті жіберіңіз және қосылуды күтіңіз!",
            protect_content=True
        )

# Обработчик отправки чека
async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    user_name = user.full_name

    try:
        logger.info(f"Inserting/updating user {user_id} ('{user_name}') with status 'pending' in handle_payment.")
        # Сохраняем данные пользователя в БД
        cur.execute(
            "INSERT INTO users (user_id, username, status) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET username = %s, status = %s",
            (user_id, user_name, 'pending', user_name, 'pending') # Ensure status is pending on conflict too
        )
        conn.commit()
        logger.info(f"User {user_id} ('{user_name}') data saved/updated with status 'pending'.")
    except psycopg2.Error as e:
        logger.error(f"Database error in handle_payment for user {user_id} ('{user_name}'): {e}")
        conn.rollback()
        await update.message.reply_text("Чекті сақтау кезінде дерекқор қатесі орын алды. Әкімшіге хабарласыңыз.", protect_content=True)
        return
    except Exception as e:
        logger.error(f"Unexpected error in handle_payment (DB part) for user {user_id} ('{user_name}'): {e}")
        await update.message.reply_text("Чекті өңдеу кезінде белгісіз қате орын алды.", protect_content=True)
        return

    # Отправляем уведомление администратору
    keyboard = [
        [InlineKeyboardButton("Растау", callback_data=f'approve_{user_id}'),
         InlineKeyboardButton("Қабылдамау", callback_data=f'reject_{user_id}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Пытаемся уведомить каждого администратора
    for admin_user_id in ADMIN_IDS:
        try:
            if update.message.photo:
                await context.bot.send_photo(
                    chat_id=admin_user_id,
                    photo=update.message.photo[-1].file_id,
                    caption=f"Жаңа чек: ID: {user_id}, Аты: {user_name}",
                    reply_markup=reply_markup,
                    protect_content=True
                )
            else: # Assuming text is a link or description of payment
                await context.bot.send_message(
                    chat_id=admin_user_id,
                    text=f"Жаңа чек: ID: {user_id}, Аты: {user_name}\nЧек мәліметі: {update.message.text}",
                    reply_markup=reply_markup,
                    protect_content=True
                )
            logger.info(f"Payment notification sent to admin {admin_user_id} for user {user_id}.")
        except Exception as e_notify:
            logger.error(f"Failed to send payment notification to admin {admin_user_id} for user {user_id}: {e_notify}")
            # Не отправляем ошибку пользователю, просто логируем проблему с конкретным админом

    # Сообщение пользователю отправляется независимо от успеха уведомления всех админов,
    # так как его чек уже обработан и сохранен в БД.
    await update.message.reply_text("Чек қабылданды! Төлемді растауды күтіңіз.", protect_content=True)

# Обработчик команды /admin
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) not in ADMIN_IDS:
        await update.message.reply_text("Бұл команда тек әкімшіге арналған.", protect_content=True)
        return

    logger.info("Admin command: Displaying filter buttons.")
    keyboard = [
        [InlineKeyboardButton("Күтудегілер (Pending)", callback_data='list_pending')],
        [InlineKeyboardButton("Мақұлданғандар (Approved)", callback_data='list_approved')],
        [InlineKeyboardButton("Бас тартылғандар (Rejected)", callback_data='list_rejected')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Пайдаланушылар тізімін таңдаңыз:", reply_markup=reply_markup, protect_content=True)

# НОВЫЙ обработчик для отображения списков пользователей по статусу
async def show_user_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    status_to_fetch = query.data.split('_')[1] # e.g., 'pending', 'approved', 'rejected'

    logger.info(f"Admin action: Fetching users with status '{status_to_fetch}'.")
    
    message_text = f"--- {status_to_fetch.capitalize()} пайдаланушылар ---"
    no_users_text = f"Қазір {status_to_fetch} статусы бар пайдаланушылар жоқ."
    users_found = False

    try:
        conn.rollback() # На всякий случай
        cur.execute("SELECT user_id, username, expiry_date FROM users WHERE status = %s", (status_to_fetch,))
        users = cur.fetchall()

        if not users:
            logger.info(f"No users found with status '{status_to_fetch}'.")
            await query.edit_message_text(text=f"{message_text}\n{no_users_text}", protect_content=True)
            return

        logger.info(f"Found {len(users)} users with status '{status_to_fetch}'.")
        await query.edit_message_text(text=message_text, protect_content=True) # Сначала заголовок списка

        for user_id, username, expiry_date in users:
            users_found = True
            user_info = f"{username} (ID: {user_id})"
            action_buttons = []

            if status_to_fetch == 'pending':
                user_info = f"Күтуде: {user_info}"
                action_buttons.append(InlineKeyboardButton("Растау", callback_data=f'approve_{user_id}'))
                action_buttons.append(InlineKeyboardButton("Қабылдамау", callback_data=f'reject_{user_id}'))
            elif status_to_fetch == 'approved':
                expiry_text = expiry_date.strftime('%d.%m.%Y') if expiry_date else "Белгісіз"
                user_info = f"Мақұлданған: {user_info} - Мерзімі: {expiry_text}"
                action_buttons.append(InlineKeyboardButton("Қабылдамау", callback_data=f'reject_{user_id}'))
                action_buttons.append(InlineKeyboardButton("Доступты алып тастау (Revoke)", callback_data=f'revoke_{user_id}'))
            elif status_to_fetch == 'rejected':
                user_info = f"Бас тартылған: {user_info}"
                action_buttons.append(InlineKeyboardButton("Растау", callback_data=f'approve_{user_id}'))
            
            reply_markup = InlineKeyboardMarkup([action_buttons]) if action_buttons else None
            await context.bot.send_message(chat_id=query.from_user.id, text=user_info, reply_markup=reply_markup, protect_content=True)

        if not users_found: # Это условие теперь избыточно из-за проверки if not users выше, но оставлю для ясности
            await context.bot.send_message(chat_id=query.from_user.id, text=no_users_text, protect_content=True)
            
    except psycopg2.Error as e:
        logger.error(f"Database error in show_user_list (status: {status_to_fetch}): {e}")
        await context.bot.send_message(chat_id=query.from_user.id, text=f"База данных қатесі ({status_to_fetch} тізімі). Әкімшіге хабарласыңыз.", protect_content=True)
        conn.rollback()
    except Exception as e:
        logger.error(f"Unexpected error in show_user_list (status: {status_to_fetch}): {e}")
        await context.bot.send_message(chat_id=query.from_user.id, text=f"Белгісіз қате ({status_to_fetch} тізімі).", protect_content=True)

# Обработчик кнопок аппрува и реджекта
async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if str(query.from_user.id) not in ADMIN_IDS:
        await query.answer("Бұл команда тек әкімшіге арналған.", show_alert=True)
        return

    await query.answer()

    action, user_id_str = query.data.split('_')
    user_id = int(user_id_str)
    
    user_name = "Пайдаланушы"
    try:
        user_chat = await context.bot.get_chat(user_id)
        user_name = user_chat.full_name or user_chat.username or f"ID: {user_id}"
    except Exception as e:
        logger.error(f"Could not get chat for user_id {user_id} in handle_admin_action: {e}")

    try:
        if action == 'approve':
            logger.info(f"Admin action: Approving user {user_id} ('{user_name}')")
            payment_date = datetime.now()
            expiry_date = payment_date + timedelta(days=90)
            cur.execute(
                "UPDATE users SET status = %s, payment_date = %s, expiry_date = %s WHERE user_id = %s",
                ('approved', payment_date, expiry_date, user_id)
            )
            conn.commit()
            logger.info(f"User {user_id} ('{user_name}') approved.")

            keyboard_lessons = []
            for i, title in enumerate(LESSON_TITLES, 1):
                keyboard_lessons.append([InlineKeyboardButton(title, callback_data=f'lesson_{i}')])
            
            reply_markup_lessons = InlineKeyboardMarkup(keyboard_lessons)
            
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ Төлем расталды! Сабақтарға қол жеткізу ашылды.\nМерзімі: {expiry_date.strftime('%d.%m.%Y')} дейін.\nТөмендегі сабақтарды таңдаңыз:",
                reply_markup=reply_markup_lessons,
                protect_content=True
            )
            confirm_text = f"Қол жеткізу {user_name} (ID: {user_id}) үшін ашылды."
            if query.message.caption is not None:
                await query.edit_message_caption(caption=confirm_text, protect_content=True)
            elif query.message.text is not None:
                await query.edit_message_text(text=confirm_text, protect_content=True)
            else: # Fallback or just remove buttons
                await query.edit_message_reply_markup(reply_markup=None)
                logger.info(f"Admin message for user {user_id} (approve) had no text/caption, buttons removed.")

        elif action == 'reject':
            logger.info(f"Admin action: Rejecting user {user_id} ('{user_name}')")
            cur.execute(
                "UPDATE users SET status = %s WHERE user_id = %s",
                ('rejected', user_id)
            )
            conn.commit()
            logger.info(f"User {user_id} ('{user_name}') rejected.")
            
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Төлем расталмады. Қайта тексеріп, чекті қайта жіберіңіз.",
                protect_content=True
            )
            reject_text = f"Қол жеткізу {user_name} (ID: {user_id}) үшін жабылды (бас тартылды)."
            if query.message.caption is not None:
                await query.edit_message_caption(caption=reject_text, protect_content=True)
            elif query.message.text is not None:
                await query.edit_message_text(text=reject_text, protect_content=True)
            else: # Fallback or just remove buttons
                await query.edit_message_reply_markup(reply_markup=None)
                logger.info(f"Admin message for user {user_id} (reject) had no text/caption, buttons removed.")

        elif action == 'revoke':
            logger.info(f"Admin action: Revoking access for user {user_id} ('{user_name}')")
            cur.execute(
                "UPDATE users SET status = %s, payment_date = NULL, expiry_date = NULL WHERE user_id = %s",
                ('pending', user_id) # Ставим статус pending, обнуляем даты
            )
            conn.commit()
            logger.info(f"Access revoked for user {user_id} ('{user_name}'). Status set to pending.")
            
            await context.bot.send_message(
                chat_id=user_id,
                text="ℹ️ Сіздің курсқа қол жеткізуіңіз әкімшімен тоқтатылды. Қосымша ақпарат алу үшін әкімшіге хабарласыңыз.",
                protect_content=True
            )
            revoke_text = f"Пайдаланушы {user_name} (ID: {user_id}) үшін қол жеткізу тоқтатылды. Енді ол күтуде."
            if query.message.caption is not None:
                await query.edit_message_caption(caption=revoke_text, protect_content=True)
            elif query.message.text is not None:
                await query.edit_message_text(text=revoke_text, protect_content=True)
            else:
                await query.edit_message_reply_markup(reply_markup=None)
                logger.info(f"Admin message for user {user_id} (revoke) had no text/caption, buttons removed.")

    except psycopg2.Error as e:
        logger.error(f"Database error in handle_admin_action for user {user_id} ('{user_name}'), action '{action}': {e}")
        conn.rollback()
        try:
            await query.edit_message_text(text=f"База данных қатесі ({action}). Әкімшіге хабарласыңыз.", protect_content=True)
        except:
             await context.bot.send_message(chat_id=query.from_user.id, text=f"База данных қатесі ({action}). Әкімшіге хабарласыңыз.", protect_content=True)
    except Exception as e:
        logger.error(f"Unexpected error in handle_admin_action for user {user_id} ('{user_name}'), action '{action}': {e}")
        try:
            await query.edit_message_text(text=f"Белгісіз қате орын алды ({action}).", protect_content=True)
        except:
            await context.bot.send_message(chat_id=query.from_user.id, text=f"Белгісіз қате орын алды ({action}).", protect_content=True)

# Обработчик выбора урока (пока просто заглушка)
async def select_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    lesson_id_str = query.data.split('_')[1]
    lesson_index = int(lesson_id_str) - 1 # Для доступа к списку LESSON_TITLES

    # Немедленно отвечаем на callback_query, чтобы избежать таймаута
    await query.answer()

    lesson_title = LESSON_TITLES[lesson_index] if 0 <= lesson_index < len(LESSON_TITLES) else f"Сабақ-{lesson_id_str}"

    try:
        conn.rollback() # Ensure fresh transaction state
        cur.execute("SELECT status FROM users WHERE user_id = %s", (user_id,))
        user_status_row = cur.fetchone()

        if not user_status_row or user_status_row[0] != 'approved':
            logger.info(f"User {user_id} tried to access lesson '{lesson_title}' but status is not 'approved'.")
            # Отправляем сообщение как обычное сообщение, а не через query.answer()
            await context.bot.send_message(
                chat_id=user_id,
                text=f"'{lesson_title}' таңдауға тырыстыңыз, бірақ курсқа қол жеткізуіңіз жабық.",
                protect_content=True
            )
            try:
                # Попытка убрать кнопки, если это возможно
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception as e_edit:
                logger.warning(f"Could not edit message for user {user_id} in select_lesson after denied access: {e_edit}")
            return

        logger.info(f"User {user_id} (status: approved) selected lesson '{lesson_title}'.")
        
        lesson_folder_path = os.path.join("lessons", lesson_title)
        logger.info(f"Looking for lesson files in: {lesson_folder_path}")

        if os.path.isdir(lesson_folder_path):
            audio_files = sorted([
                f for f in os.listdir(lesson_folder_path) 
                if os.path.isfile(os.path.join(lesson_folder_path, f)) and 
                   f.lower().endswith(('.mp3', '.m4a', '.ogg', '.wav', '.opus'))
            ])

            if audio_files:
                await context.bot.send_message(chat_id=user_id, text=f"'{lesson_title}' сабағының материалдары жіберілуде...", protect_content=True) # Изменено с query.message.reply_text
                for audio_file_name in audio_files:
                    audio_file_path = os.path.join(lesson_folder_path, audio_file_name)
                    try:
                        logger.info(f"Sending audio: {audio_file_path} to user {user_id}")
                        with open(audio_file_path, 'rb') as audio_fp:
                            await context.bot.send_audio(
                                chat_id=user_id, 
                                audio=audio_fp, 
                                caption=audio_file_name,
                                protect_content=True
                            )
                        logger.info(f"Successfully sent {audio_file_name}")
                    except Exception as e_send_audio:
                        logger.error(f"Failed to send audio file {audio_file_path} to user {user_id}: {e_send_audio}")
                        await context.bot.send_message(chat_id=user_id, text=f"'{audio_file_name}' файлын жіберу кезінде қате орын алды.", protect_content=True)
                await context.bot.send_message(chat_id=user_id, text=f"'{lesson_title}' сабағының барлық материалдары жіберілді.", protect_content=True)
            else:
                logger.info(f"No audio files found in {lesson_folder_path}.")
                await context.bot.send_message(chat_id=user_id, text=f"'{lesson_title}' сабағы үшін аудио материалдар әзірге жоқ немесе табылмады.", protect_content=True) # Изменено с query.message.reply_text
        else:
            logger.warning(f"Lesson folder not found: {lesson_folder_path}")
            await context.bot.send_message(chat_id=user_id, text=f"'{lesson_title}' сабағының материалдары табылмады. Әкімшіге хабарласыңыз.", protect_content=True) # Изменено с query.message.reply_text

    except psycopg2.Error as e:
        logger.error(f"Database error in select_lesson for user {user_id}, lesson '{lesson_title}': {e}")
        # query.answer() уже был вызван
        await context.bot.send_message(chat_id=user_id, text="Дерекқор қатесі орын алды. Әкімшіге хабарласыңыз.", protect_content=True)
        conn.rollback()
    except Exception as e:
        logger.error(f"Unexpected error in select_lesson for user {user_id}, lesson '{lesson_title}': {e}")
        # query.answer() уже был вызван
        await context.bot.send_message(chat_id=user_id, text="Белгісіз қате орын алды. Әкімшіге хабарласыңыз.", protect_content=True)

# Обработчик команды /approve (для обратной совместимости)
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) not in ADMIN_IDS:
        await update.message.reply_text("Бұл команда тек әкімшіге арналған.", protect_content=True)
        return
    try:
        user_id = int(context.args[0])
        logger.info(f"Legacy /approve command for user_id: {user_id}")
        payment_date = datetime.now()
        expiry_date = payment_date + timedelta(days=90)
        cur.execute(
            "UPDATE users SET status = %s, payment_date = %s, expiry_date = %s WHERE user_id = %s",
            ('approved', payment_date, expiry_date, user_id)
        )
        conn.commit()
        logger.info(f"User {user_id} approved via legacy /approve.")

        keyboard_legacy_lessons = []
        for i, title in enumerate(LESSON_TITLES, 1):
            keyboard_legacy_lessons.append([InlineKeyboardButton(title, callback_data=f'lesson_{i}')])
        
        reply_markup = InlineKeyboardMarkup(keyboard_legacy_lessons)
        
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Төлем расталды! Сабақтарға қол жеткізу ашылды (legacy /approve арқылы).\nМерзімі: {expiry_date.strftime('%d.%m.%Y')} дейін.\nТөмендегі сабақтарды таңдаңыз:",
            reply_markup=reply_markup,
            protect_content=True
        )
        await update.message.reply_text(f"Қол жеткізу ID: {user_id} үшін ашылды (legacy /approve).", protect_content=True)
    except (IndexError, ValueError):
        await update.message.reply_text("Пайдалану: /approve <user_id>", protect_content=True)
    except psycopg2.Error as e:
        logger.error(f"Database error in legacy /approve for user_id {context.args[0] if context.args else 'N/A'}: {e}")
        conn.rollback()
        await update.message.reply_text("База данных қатесі (/approve). Әкімшіге хабарласыңыз.", protect_content=True)
    except Exception as e:
        logger.error(f"Unexpected error in legacy /approve for user_id {context.args[0] if context.args else 'N/A'}: {e}")
        await update.message.reply_text("Белгісіз қате орын алды (/approve).", protect_content=True)

# Обработчик команды /reject (для обратной совместимости)
async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) not in ADMIN_IDS:
        await update.message.reply_text("Бұл команда тек әкімшіге арналған.", protect_content=True)
        return
    try:
        user_id = int(context.args[0])
        logger.info(f"Legacy /reject command for user_id: {user_id}")
        cur.execute(
            "UPDATE users SET status = %s WHERE user_id = %s",
            ('rejected', user_id)
        )
        conn.commit()
        logger.info(f"User {user_id} rejected via legacy /reject.")

        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Төлем расталмады (legacy /reject арқылы). Қайта тексеріп, чекті қайта жіберіңіз.",
            protect_content=True
        )
        await update.message.reply_text(f"Қол жеткізу ID: {user_id} үшін жабылды (legacy /reject).", protect_content=True)
    except (IndexError, ValueError):
        await update.message.reply_text("Пайдалану: /reject <user_id>", protect_content=True)
    except psycopg2.Error as e:
        logger.error(f"Database error in legacy /reject for user_id {context.args[0] if context.args else 'N/A'}: {e}")
        conn.rollback()
        await update.message.reply_text("База данных қатесі (/reject). Әкімшіге хабарласыңыз.", protect_content=True)
    except Exception as e:
        logger.error(f"Unexpected error in legacy /reject for user_id {context.args[0] if context.args else 'N/A'}: {e}")
        await update.message.reply_text("Белгісіз қате орын алды (/reject).", protect_content=True)

# Основная функция
def main():
    try:
        # Загружаем file_id из базы данных при запуске
        load_video_file_id()
        
        # Создаем приложение и добавляем обработчики
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(next_step, pattern='next'))
        application.add_handler(CallbackQueryHandler(button, pattern='start'))
        application.add_handler(CallbackQueryHandler(get_access, pattern='get_access'))
        application.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_payment))
        application.add_handler(CommandHandler("admin", admin))
        application.add_handler(CallbackQueryHandler(show_user_list, pattern='^list_(pending|approved|rejected)$'))
        application.add_handler(CallbackQueryHandler(handle_admin_action, pattern='^(approve|reject|revoke)_\\d+$'))
        application.add_handler(CallbackQueryHandler(select_lesson, pattern='^lesson_\\d+$'))
        application.add_handler(CommandHandler("approve", approve))
        application.add_handler(CommandHandler("reject", reject))
        
        logger.info("Бот запускается...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
        logger.info("Бот остановлен.")
        cur.close()
        conn.close()
    except Exception as e:
        logger.critical(f"Critical error in main function: {e}")
        raise e

if __name__ == '__main__':
    main()