from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import psycopg2
from datetime import datetime, date, time, timedelta
import logging
import os
import re # Добавлен импорт re
from telegram.error import NetworkError, TelegramError # Добавляем импорт

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# API-токен бота из переменной окружения или значения по умолчанию
TOKEN = os.environ.get('TOKEN', '7339317818:AAEeTxHPrd0BsqSlMFk41ZFMdvp33t8DyjU')

# Telegram ID администратора
ADMIN_IDS = ['1645154232'] # Должен быть список, даже с одним ID
# Названия уроков (ОБНОВЛЕНО согласно списку папок пользователя)
LESSON_TITLES = [
    "1 сабақ. Орталық Азия және Ұлы Дала",
    "2 сабақ. Қазақстан  территориясындағы тас ,қола және темір дәуірлері",
    "3 сабақ. Қазақстан территориясындағы алғашқы тайпалық одақтар мен ертедегі мемлекеттер",
    "4 сабақ. Ерте орта ғасырлардағы Қазақстан  тарихы",
    "5 сабақ. VI-IX ғасырлардағы Қазақстан  мәдениеті",
    "6 сабақ. Дамыған орта ғасырлар мемлекеттерінің тарихы",
    "7 сабақ. IX-XIII ғасырлардағы Қазақстан  мәдениеті",
    "8 сабақ. Кейінгі орта ғасырлар тарихы.(XIII-XVII ғасырлар)",
    "9 сабақ. XIII-XV ғасырдың бірінші жартысындағы мемлекеттердің саяси құрылымы, экономикасы және мәдениеті",
    "10 сабақ. Біртұтас Қазақ мемлекетінің құрылуы",
    "11 сабақ. XV-XVII ғасырлардағы Қазақ хандығының әлеуметтік-экономикалық дамуы және мәдениеті",
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

# Вспомогательная функция для извлечения числового префикса из имени файла
def extract_number_prefix(filename):
    # Ищем одну или более цифр в начале имени файла, возможно, с пробелами до них
    match = re.match(r"^\\s*(\\d+)", filename)
    if match:
        return int(match.group(1))
    # Если числовой префикс не найден, файл будет отсортирован в конец
    # или по алфавиту после файлов с префиксами, в зависимости от вторичного ключа сортировки
    return float('inf')


# Функция для загрузки file_id из базы данных
def load_video_file_id():
    # Намеренно НЕ загружаем file_id из базы данных
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

# Новая вспомогательная функция для создания клавиатуры уроков
def create_lesson_keyboard():
    keyboard_lessons = []
    if not LESSON_TITLES:
        return InlineKeyboardMarkup(keyboard_lessons) # Возвращаем пустую клавиатуру, если нет названий

    # Находим максимальную длину названия урока
    max_len = 0
    for title in LESSON_TITLES:
        if len(title) > max_len:
            max_len = len(title)
    
    # Создаем кнопки, дополняя короткие названия пробелами
    for i, title in enumerate(LESSON_TITLES, 1):
        # Используем ljust для выравнивания по левому краю, добавляя пробелы справа
        # Небольшой отступ для красоты, если нужно, или просто max_len
        formatted_title = title.ljust(max_len) 
        keyboard_lessons.append([InlineKeyboardButton(formatted_title, callback_data=f'lesson_{i}')])
    
    return InlineKeyboardMarkup(keyboard_lessons)



# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("әрі қарай", callback_data='next')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await update.message.reply_text(
            "\"Тарихшы Нұрсұлтан\" Telegram каналына қош келдіңіз! 📚",
            reply_markup=reply_markup,
            protect_content=True
        )
    except NetworkError as e:
        logger.error(f"Network error in start handler sending welcome message: {e}", exc_info=True)

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
        try:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text="Фото файлы табылмады. Әкімшіге хабарласыңыз.",
                protect_content=True
            )
        except NetworkError as e:
            logger.error(f"Network error in next_step handler sending photo not found error: {e}", exc_info=True)
    except NetworkError as e:
        logger.error(f"Network error sending photo in next_step handler: {e}", exc_info=True)
        # Optionally, inform user if photo sending failed due to network, though it might also fail
        try:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text="Фотоны жіберу кезінде желі қатесі орын алды.",
                protect_content=True
            )
        except NetworkError as ne_inner:
            logger.error(f"Network error in next_step handler sending photo network error message: {ne_inner}", exc_info=True)
    except Exception as e:
        logger.error(f"Error sending photo in next_step handler: {e}", exc_info=True)
        try:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text="Фотоны жіберу кезінде қате орын алды.",
                protect_content=True
            )
        except NetworkError as ne_generic_error:
                 logger.error(f"Network error sending generic photo error message: {ne_generic_error}", exc_info=True)
    
    # Сразу отправляем текст об авторе с кнопкой "start"
    keyboard = [[InlineKeyboardButton("start", callback_data='start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    author_text = (
        "Тәжен Нұрсұлтан Шәутенұлы\n\n"
        "Қырық жылға жуық еңбек өтілі бар Педагог-шебер,\n"
        "ҚР 'Білім беру ісінің үздігі',\n"
        "'Ы. Алтынсарин төсбелгісінің' иегері,\n"
        "Қазақстан тарихы пәні бойынша бірнеше әдістемелік құралдардың авторы."
        )
    try:
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=author_text,
            reply_markup=reply_markup,
            protect_content=True
        )
    except NetworkError as e:
        logger.error(f"Network error in next_step handler sending author text: {e}", exc_info=True)

# Обработчик кнопки "Старт"
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    logger.info(f"Button handler called with query.data: {query.data}")
    await query.answer()
    if query.data == 'start':
        keyboard = [[InlineKeyboardButton("Сабақтарға қол жеткізгім келеді!", callback_data='get_access')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        global VIDEO_FILE_ID
        video_path = 'video1.mp4'  # Путь к вашему видео файлу

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
            try:
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text="Видео файлы табылмады. Әкімшіге хабарласыңыз.",
                    reply_markup=reply_markup,
                    protect_content=True
                )
            except NetworkError as e_fnf:
                logger.error(f"Network error sending video not found message: {e_fnf}", exc_info=True)
        except NetworkError as e_net:
            logger.error(f"Network error sending video in button handler: {e_net}", exc_info=True)
            try:
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text="Видеоны жіберу кезінде желі қатесі орын алды. Сізге бәрібір жалғастыруға мүмкіндік береміз.",
                    reply_markup=reply_markup,
                    protect_content=True
                )
            except NetworkError as e_net_fallback:
                logger.error(f"Network error sending video fallback message: {e_net_fallback}", exc_info=True)
        except Exception as e:
            logger.error(f"Error sending video in button handler: {e}", exc_info=True)
            try:
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text="Видеоны жіберу кезінде қате орын алды. Сізге бәрібір жалғастыруға мүмкіндік береміз.",
                    reply_markup=reply_markup,
                    protect_content=True
                )
            except NetworkError as e_generic_fallback:
                 logger.error(f"Network error sending video generic fallback message: {e_generic_fallback}", exc_info=True)

# Обработчик кнопки "Сабақтарға қол жеткізгім келеді!"
async def get_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    logger.info(f"Get_access handler called with query.data: {query.data}")
    await query.answer()
    if query.data == 'get_access':
        # Кнопка для оплаты через Kaspi Pay
        keyboard = [[InlineKeyboardButton("Төлем жасау", url='https://pay.kaspi.kz/pay/2tyi0ezv')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.message.reply_text(
        "💰 Курс туралы ақпарат:\n\n"
        "Аудио сабақтарды пайдалану мерзімі - 12 ай.\n"
        "Бағасы - 48 000 теңге.\n"
        "Осы төлемді төлеп, каналға қосылыңыз.\n\n"
        "Каналға қосылу сізге 12 ай бойы Тәжен Нұрсұлтанның Қазақстан тарихы пәнінен "
        "124 тақырыпты қамтитын авторлық аудио сабақтарын тыңдауға мүмкіндік береді!\n\n"
        "Чекті скриншот (фото) немесе PDF форматында жіберуіңізді сұраймыз!",
        reply_markup=reply_markup,
        protect_content=True
    )
        except NetworkError as e:
            logger.error(f"Network error in get_access sending course info: {e}", exc_info=True)
        
        try:
            # Сообщение сразу после нажатия кнопки
            await query.message.reply_text(
                "Чекті жіберіңіз және қосылуды күтіңіз!",
                protect_content=True
            )
        except NetworkError as e:
            logger.error(f"Network error in get_access sending check prompt: {e}", exc_info=True)

# Обработчик отправки чека
async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    user_name = user.full_name

    # Логируем тип сообщения для отладки
    logger.info(f"handle_payment called for user {user_id} ('{user_name}')")
    logger.info(f"Message type - Photo: {bool(update.message.photo)}, Document: {bool(update.message.document)}, Text: {bool(update.message.text)}")
    if update.message.document:
        logger.info(f"Document mime_type: {update.message.document.mime_type}")

    try:
        # Сначала проверяем текущий статус пользователя
        cur.execute("SELECT status, expiry_date FROM users WHERE user_id = %s", (user_id,))
        user_data = cur.fetchone()

        # Если пользователь найден, статус 'approved' и срок не истек
        if user_data and user_data[0] == 'approved' and user_data[1]:
            expiry_dt = user_data[1]
            if isinstance(expiry_dt, date) and not isinstance(expiry_dt, datetime):
                expiry_dt = datetime.combine(expiry_dt, time.min)

            if expiry_dt > datetime.now():
                logger.info(f"User {user_id} ('{user_name}') already has approved status with valid expiry date.")
                reply_markup = create_lesson_keyboard()
                try:
                    await update.message.reply_text(
                        f"Сізде сабақтарға қол жеткізу ашық! Мерзімі: {user_data[1].strftime('%d.%m.%Y')}. Төмендегі сабақтарды таңдаңыз:",
                        reply_markup=reply_markup,
                        protect_content=True
                    )
                except NetworkError as e:
                    logger.error(f"Network error sending already approved message: {e}", exc_info=True)

                # Если это текстовое сообщение - добавляем сообщение с командами в конце
                if update.message.text:
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text="📞 Әкімшіге хабарлама жіберу үшін команданы келесі түрде пайдаланыңыз:\n\n"
                                 "🔸 /admin_khabar Сіздің хабарламаңыз\n\n"
                                 "📝 Мысал:\n"
                                 "/admin_khabar Сабақтар ашылмай тұр\n\n"
                                 "⚠️ Команда мен хабарламаның арасында бос орын қалдырыңыз!",
                            protect_content=True
                        )
                    except NetworkError as e:
                        logger.error(f"Network error sending admin contact info to approved user: {e}", exc_info=True)

                return
    except Exception as e:
        logger.error(f"Error checking user status: {e}", exc_info=True)

    keyboard = [
        [InlineKeyboardButton("Растау", callback_data=f'approve_{user_id}'),
         InlineKeyboardButton("Қабылдамау", callback_data=f'reject_{user_id}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Сначала проверяем, что это действительно фото, изображение или PDF
    is_image = update.message.photo or (update.message.document and update.message.document.mime_type and
                                       (update.message.document.mime_type.startswith('image/') or
                                        update.message.document.mime_type == 'application/pdf'))

    if not is_image:
        if update.message.text:
            logger.info(f"User {user_id} sent text message instead of photo/PDF: {update.message.text}")
            try:
                await update.message.reply_text(
                    "⚠️ Сіз тек сурет немесе PDF файл жібере аласыз!\n\n"
                    "📞 Егер сізге көмек керек болса, қолданыңыз:\n"
                    "🔸 /admin_khabar сіздің хабарламаңыз\n\n"
                    "📝 Мысал: /admin_khabar Сабақтар ашылмай тұр",
                    protect_content=True
                )
            except NetworkError as e:
                logger.error(f"Network error sending text filter message: {e}", exc_info=True)
        return  # Не отправляем админу и не сохраняем в базу

    # Отправляем файл всем админам
    admin_notification_success = False
    for admin_user_id in ADMIN_IDS:
        try:
            if update.message.photo:
                logger.info(f"Sending photo to admin {admin_user_id} from user {user_id}")
                await context.bot.send_photo(
                    chat_id=admin_user_id,
                    photo=update.message.photo[-1].file_id,
                    caption=f"Жаңа чек: ID: {user_id}, Аты: {user_name}",
                    reply_markup=reply_markup,
                    protect_content=True
                )
                logger.info(f"Photo successfully sent to admin {admin_user_id}")
            elif update.message.document:
                if update.message.document.mime_type == 'application/pdf':
                    logger.info(f"Sending PDF to admin {admin_user_id} from user {user_id}")
                    await context.bot.send_document(
                        chat_id=admin_user_id,
                        document=update.message.document.file_id,
                        caption=f"Жаңа PDF чек: ID: {user_id}, Аты: {user_name}",
                        reply_markup=reply_markup,
                        protect_content=True
                    )
                    logger.info(f"PDF successfully sent to admin {admin_user_id}")
                elif update.message.document.mime_type and update.message.document.mime_type.startswith('image/'):
                    logger.info(f"Sending image document to admin {admin_user_id} from user {user_id}")
                    await context.bot.send_document(
                        chat_id=admin_user_id,
                        document=update.message.document.file_id,
                        caption=f"Жаңа сурет чек: ID: {user_id}, Аты: {user_name}",
                        reply_markup=reply_markup,
                        protect_content=True
                    )
                    logger.info(f"Image document successfully sent to admin {admin_user_id}")

            admin_notification_success = True
            logger.info(f"Payment notification sent to admin {admin_user_id} for user {user_id}.")
        except NetworkError as e_admin_notify:
            logger.error(f"Network error sending payment notification to admin {admin_user_id} for user {user_id}: {e_admin_notify}", exc_info=True)
        except Exception as e_notify:
            logger.error(f"Failed to send payment notification to admin {admin_user_id} for user {user_id}: {e_notify}", exc_info=True)

    # Если не удалось отправить ни одному админу, не сохраняем в базу
    if not admin_notification_success:
        logger.error(f"Failed to send payment notification to any admin for user {user_id}")
        try:
            await update.message.reply_text("Чекті жіберу кезінде қате орын алды. Қайталап көріңіз.", protect_content=True)
        except NetworkError as e:
            logger.error(f"Network error sending failure message to user: {e}", exc_info=True)
        return

    # Сохраняем в БД только после успешной отправки админу
    try:
        logger.info(f"Inserting/updating user {user_id} ('{user_name}') with status 'pending' in handle_payment.")
        cur.execute(
            "INSERT INTO users (user_id, username, status) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET username = %s, status = %s",
            (user_id, user_name, 'pending', user_name, 'pending')
        )
        conn.commit()
        logger.info(f"User {user_id} ('{user_name}') data saved/updated with status 'pending'.")
    except psycopg2.Error as e_db:
        logger.error(f"Database error in handle_payment for user {user_id} ('{user_name}'): {e_db}", exc_info=True)
        conn.rollback()
        try:
            await update.message.reply_text("Чекті сақтау кезінде дерекқор қатесі орын алды. Әкімшіге хабарласыңыз.", protect_content=True)
        except NetworkError as e_net:
            logger.error(f"Network error sending DB error message in handle_payment: {e_net}", exc_info=True)
        return
    except Exception as e_generic:
        logger.error(f"Unexpected error in handle_payment (DB part) for user {user_id} ('{user_name}'): {e_generic}", exc_info=True)
        try:
            await update.message.reply_text("Чекті өңдеу кезінде белгісіз қате орын алды.", protect_content=True)
        except NetworkError as e_net:
            logger.error(f"Network error sending generic error message in handle_payment: {e_net}", exc_info=True)
        return

    # Подтверждение отправляем только если это был чек (фото, изображение или PDF)
    if is_image:
        try:
            await update.message.reply_text("Чекіңізді әкімші қарап жатқанша күте тұрыңыз.", protect_content=True)
            logger.info(f"Confirmation sent to user {user_id}: check received and waiting for admin review.")
        except NetworkError as e:
            logger.error(f"Network error sending check received confirmation to user: {e}", exc_info=True)
    else:
        logger.info(f"No confirmation sent to user {user_id} - message was not a photo, image or PDF.")

# Обработчик команды /admin
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) not in ADMIN_IDS:
        try:
            await update.message.reply_text("Бұл команда тек әкімшіге арналған.", protect_content=True)
        except NetworkError as e:
            logger.error(f"Network error in admin handler sending auth error: {e}", exc_info=True)
        return

    logger.info("Admin command: Displaying filter buttons.")
    keyboard = [
        [InlineKeyboardButton("Күтудегілер (Pending)", callback_data='list_pending')],
        [InlineKeyboardButton("Мақұлданғандар (Approved)", callback_data='list_approved')],
        [InlineKeyboardButton("Бас тартылғандар (Rejected)", callback_data='list_rejected')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await update.message.reply_text("Пайдаланушылар тізімін таңдаңыз:", reply_markup=reply_markup, protect_content=True)
    except NetworkError as e:
        logger.error(f"Network error in admin handler sending user list prompt: {e}", exc_info=True)

# НОВЫЙ обработчик для отображения списков пользователей по статусу
async def show_user_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    status_to_fetch = query.data.split('_')[1] 

    logger.info(f"Admin action: Fetching users with status '{status_to_fetch}'.")
    
    message_text_header = f"--- {status_to_fetch.capitalize()} пайдаланушылар ---"
    no_users_text = f"Қазір {status_to_fetch} статусы бар пайдаланушылар жоқ."

    try:
        # Попытка изменить исходное сообщение на заголовок списка
        try:
            await query.edit_message_text(text=message_text_header)
        except NetworkError as e_net_edit_header:
            logger.error(f"Network error editing message to header in show_user_list ({status_to_fetch}): {e_net_edit_header}", exc_info=True)
            # Если редактирование не удалось из-за сети, пробуем отправить как новое сообщение
            try:
                await context.bot.send_message(chat_id=query.from_user.id, text=message_text_header, protect_content=True)
            except NetworkError as e_net_send_header:
                logger.error(f"Network error sending header as new message in show_user_list ({status_to_fetch}): {e_net_send_header}", exc_info=True)
                return # Если даже заголовок не отправить, выходим
        except TelegramError as e_tele_edit_header: # Другие ошибки Telegram API при редактировании
            logger.error(f"Telegram API error editing message to header in show_user_list ({status_to_fetch}): {e_tele_edit_header}", exc_info=True)
            try:
                await context.bot.send_message(chat_id=query.from_user.id, text=message_text_header, protect_content=True)
            except (NetworkError, TelegramError) as e_send_header_fallback:
                logger.error(f"Error sending header as new message (fallback) in show_user_list ({status_to_fetch}): {e_send_header_fallback}", exc_info=True)
                return

        conn.rollback() 
        cur.execute("SELECT user_id, username, expiry_date FROM users WHERE status = %s", (status_to_fetch,))
        users = cur.fetchall()

        if not users:
            logger.info(f"No users found with status '{status_to_fetch}'.")
            # Сообщение о том, что пользователи не найдены, отправляем как новое, т.к. заголовок уже мог быть отправлен
            try:
                await context.bot.send_message(chat_id=query.from_user.id, text=no_users_text, protect_content=True)
            except (NetworkError, TelegramError) as e_no_users:
                logger.error(f"Error sending 'no users found' message in show_user_list ({status_to_fetch}): {e_no_users}", exc_info=True)
            return

        logger.info(f"Found {len(users)} users with status '{status_to_fetch}'.")

        for user_id, username, expiry_date in users:
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
            
            reply_markup_user = InlineKeyboardMarkup([action_buttons]) if action_buttons else None
            try:
                await context.bot.send_message(chat_id=query.from_user.id, text=user_info, reply_markup=reply_markup_user, protect_content=True)
            except NetworkError as e_net_user_info:
                logger.error(f"Network error sending user info for {user_id} in show_user_list ({status_to_fetch}): {e_net_user_info}", exc_info=True)
            except TelegramError as e_tele_user_info:
                logger.error(f"Telegram API error sending user info for {user_id} in show_user_list ({status_to_fetch}): {e_tele_user_info}", exc_info=True)
            
    except psycopg2.Error as e_db:
        logger.error(f"Database error in show_user_list (status: {status_to_fetch}): {e_db}", exc_info=True)
        try:
            # Если исходное сообщение было изменено на заголовок, пробуем его изменить на ошибку
            # Иначе отправляем новое сообщение об ошибке
            if query.message and query.message.text == message_text_header: 
                await query.edit_message_text(text=f"База данных қатесі ({status_to_fetch} тізімі).")
            else:
                await context.bot.send_message(chat_id=query.from_user.id, text=f"База данных қатесі ({status_to_fetch} тізімі). Әкімшіге хабарласыңыз.", protect_content=True)
        except (NetworkError, TelegramError) as e_report_db_err:
            logger.error(f"Error reporting DB error to admin in show_user_list ({status_to_fetch}): {e_report_db_err}", exc_info=True)
        conn.rollback()
    except Exception as e_generic:
        logger.error(f"Unexpected error in show_user_list (status: {status_to_fetch}): {e_generic}", exc_info=True)
        try:
            if query.message and query.message.text == message_text_header:
                 await query.edit_message_text(text=f"Белгісіз қате ({status_to_fetch} тізімі).")
            else:
                await context.bot.send_message(chat_id=query.from_user.id, text=f"Белгісіз қате ({status_to_fetch} тізімі).", protect_content=True)
        except (NetworkError, TelegramError) as e_report_gen_err:
            logger.error(f"Error reporting generic error to admin in show_user_list ({status_to_fetch}): {e_report_gen_err}", exc_info=True)

# Обработчик кнопок аппрува и реджекта
async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin_chat_id = query.from_user.id # ID админа, который нажал кнопку
    
    if str(admin_chat_id) not in ADMIN_IDS:
        try:
            await query.answer("Бұл команда тек әкімшіге арналған.", show_alert=True)
        except (NetworkError, TelegramError) as e_ans_auth:
            logger.warning(f"Error answering callback query for auth in handle_admin_action: {e_ans_auth}")
            return

    try:
        await query.answer() # Отвечаем на callback
    except (NetworkError, TelegramError) as e_ans_main:
        logger.warning(f"Error answering callback query in handle_admin_action: {e_ans_main}")
        # Продолжаем выполнение, т.к. это не критично для логики, но админ не увидит "часики"

    action, user_id_str = query.data.split('_')
    user_id = int(user_id_str)
    
    user_name = f"Пайдаланушы (ID: {user_id})" # Default name
    try:
        user_chat = await context.bot.get_chat(user_id)
        user_name = user_chat.full_name or user_chat.username or f"ID: {user_id}"
    except (NetworkError, TelegramError) as e_get_chat:
        logger.error(f"Could not get chat for user_id {user_id} in handle_admin_action: {e_get_chat}", exc_info=True)
        # Продолжаем с user_name по умолчанию
    except Exception as e_get_chat_other:
        logger.error(f"Unexpected error getting chat for user_id {user_id}: {e_get_chat_other}", exc_info=True)

    admin_confirm_text = ""
    user_notification_text = ""
    db_success = False

    try:
        if action == 'approve':
            logger.info(f"Admin action: Approving user {user_id} ('{user_name}')")
            payment_date = datetime.now()
            expiry_date_val = payment_date + timedelta(days=365) # 12 месяцев
            cur.execute(
                "UPDATE users SET status = %s, payment_date = %s, expiry_date = %s WHERE user_id = %s",
                ('approved', payment_date, expiry_date_val, user_id)
            )
            conn.commit()
            db_success = True
            logger.info(f"User {user_id} ('{user_name}') approved in DB.")

            reply_markup_lessons = create_lesson_keyboard()
            user_notification_text = f"""✅ Төлем расталды! Сабақтарға қол жеткізу ашылды.
Мерзімі: {expiry_date_val.strftime('%d.%m.%Y')} дейін.
Төмендегі сабақтарды таңдаңыз:"""
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=user_notification_text,
                    reply_markup=reply_markup_lessons,
                    protect_content=True
                )
                logger.info(f"Approval notification sent to user {user_id}.")
            except (NetworkError, TelegramError) as e_user_approve_notify:
                logger.error(f"Error sending approval notification to user {user_id}: {e_user_approve_notify}", exc_info=True)
            
            admin_confirm_text = f"{user_name} (ID: {user_id}) үшін қол жеткізу ашылды."

        elif action == 'reject':
            logger.info(f"Admin action: Rejecting user {user_id} ('{user_name}')")
            cur.execute(
                "UPDATE users SET status = %s WHERE user_id = %s",
                ('rejected', user_id)
            )
            conn.commit()
            db_success = True
            logger.info(f"User {user_id} ('{user_name}') rejected in DB.")
            
            user_notification_text = "❌ Төлем расталмады. Қайта тексеріп, чекті қайта жіберіңіз."
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=user_notification_text,
                    protect_content=True
                )
                logger.info(f"Rejection notification sent to user {user_id}.")
            except (NetworkError, TelegramError) as e_user_reject_notify:
                logger.error(f"Error sending rejection notification to user {user_id}: {e_user_reject_notify}", exc_info=True)
            
            admin_confirm_text = f"{user_name} (ID: {user_id}) үшін қол жеткізу жабылды (бас тартылды)."

        elif action == 'revoke':
            logger.info(f"Admin action: Revoking access for user {user_id} ('{user_name}')")
            cur.execute(
                "UPDATE users SET status = %s, payment_date = NULL, expiry_date = NULL WHERE user_id = %s",
                ('pending', user_id) 
            )
            conn.commit()
            db_success = True
            logger.info(f"Access revoked for user {user_id} ('{user_name}') in DB. Status set to pending.")
            
            user_notification_text = "ℹ️ Сіздің курсқа қол жеткізуіңіз әкімшімен тоқтатылды. Қосымша ақпарат алу үшін әкімшіге хабарласыңыз."
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=user_notification_text,
                    protect_content=True
                )
                logger.info(f"Revoke notification sent to user {user_id}.")
            except (NetworkError, TelegramError) as e_user_revoke_notify:
                logger.error(f"Error sending revoke notification to user {user_id}: {e_user_revoke_notify}", exc_info=True)

            admin_confirm_text = f"Пайдаланушы {user_name} (ID: {user_id}) үшін қол жеткізу тоқтатылды. Енді ол күтуде."

        # Update admin's message only if DB operation was successful
        if db_success and admin_confirm_text:
            try:
                if query.message.caption is not None:
                    # Для сообщений с изображением/документом - редактируем подпись
                    await query.edit_message_caption(caption=admin_confirm_text)
                elif query.message.text is not None:
                    # Для текстовых сообщений - редактируем текст
                    await query.edit_message_text(text=admin_confirm_text)
                else:
                    # Если нет ни текста, ни подписи - просто убираем кнопки
                    await query.edit_message_reply_markup(reply_markup=None)
                    logger.info(f"Admin message (original with buttons for {user_id}, action {action}) had no text/caption, buttons removed.")
            except (NetworkError, TelegramError) as e_admin_edit:
                logger.error(f"Error updating admin's original message for user {user_id}, action {action}: {e_admin_edit}", exc_info=True)
                # Fallback: send new message to admin if edit fails
                try:
                    await context.bot.send_message(chat_id=admin_chat_id, text=f"✅ {admin_confirm_text}", protect_content=True)
                except (NetworkError, TelegramError) as e_admin_fallback:
                    logger.error(f"Error sending admin fallback confirmation for {action} user {user_id}: {e_admin_fallback}", exc_info=True)

    except psycopg2.Error as e_db_main:
        logger.error(f"Database error in handle_admin_action for user {user_id} ('{user_name}'), action '{action}': {e_db_main}", exc_info=True)
        conn.rollback()
        error_message_for_admin = f"❌ База данных қатесі ({action} {user_name}). Әкімшіге хабарласыңыз."
        try:
            # Отправляем новое сообщение об ошибке вместо попытки редактирования
            await context.bot.send_message(chat_id=admin_chat_id, text=error_message_for_admin, protect_content=True)
        except (NetworkError, TelegramError) as e_report_db_err_admin:
             logger.error(f"Error reporting DB error to admin in handle_admin_action: {e_report_db_err_admin}", exc_info=True)

    except Exception as e_generic_main:
        logger.error(f"Unexpected error in handle_admin_action for user {user_id} ('{user_name}'), action '{action}': {e_generic_main}", exc_info=True)
        error_message_for_admin = f"⚠️ Белгісіз қате орын алды ({action} {user_name})."
        try:
            # Отправляем новое сообщение об ошибке вместо попытки редактирования
            await context.bot.send_message(chat_id=admin_chat_id, text=error_message_for_admin, protect_content=True)
        except (NetworkError, TelegramError) as e_report_gen_err_admin:
            logger.error(f"Error reporting generic error to admin in handle_admin_action: {e_report_gen_err_admin}", exc_info=True)

# Обработчик выбора урока
async def select_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    lesson_id_str = query.data.split('_')[1]
    lesson_index = int(lesson_id_str) - 1 

    await query.answer()

    lesson_title = LESSON_TITLES[lesson_index] if 0 <= lesson_index < len(LESSON_TITLES) else f"Сабақ-{lesson_id_str}"

    try:
        conn.rollback() 
        cur.execute("SELECT status FROM users WHERE user_id = %s", (user_id,))
        user_status_row = cur.fetchone()

        if not user_status_row or user_status_row[0] != 'approved':
            logger.info(f"User {user_id} tried to access lesson '{lesson_title}' but status is not 'approved'.")
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"'{lesson_title}' таңдауға тырыстыңыз, бірақ курсқа қол жеткізуіңіз жабық.",
                    protect_content=True
                )
            except NetworkError as e:
                logger.error(f"Network error sending access denied message in select_lesson: {e}", exc_info=True)
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except NetworkError as e_edit_nm: # NetworkError
                logger.warning(f"Network error editing message reply markup in select_lesson (denied access): {e_edit_nm}", exc_info=True)
            except Exception as e_edit: # Other errors like message not modified, etc.
                logger.warning(f"Could not edit message for user {user_id} in select_lesson after denied access: {e_edit}", exc_info=True)
            return

        logger.info(f"User {user_id} (status: approved) selected lesson '{lesson_title}' (index: {lesson_index}).")
        
        lesson_folder_path = os.path.join("lessons", lesson_title)
        logger.info(f"Looking for lesson files in: {lesson_folder_path}")

        if os.path.isdir(lesson_folder_path):
            raw_audio_files = [
                f for f in os.listdir(lesson_folder_path) 
                if os.path.isfile(os.path.join(lesson_folder_path, f)) and 
                   f.lower().endswith(('.mp3', '.m4a', '.ogg', '.wav', '.opus'))
            ]

            problematic_lesson_indices = [4, 6, 9, 11, 20, 24] 
            audio_files_sorted = []
            if lesson_index in problematic_lesson_indices:
                logger.info(f"Applying SPECIAL sorting for problematic lesson: '{lesson_title}' (index {lesson_index})")
                
                def get_sort_key_for_problematic(filename):
                    # Priority 0: "с- ЧИСЛО т" pattern (handles spaces)
                    match_sc_t = re.search(r'с-\s*(\d+)\s*т', filename, re.IGNORECASE)
                    if match_sc_t:
                        return (0, int(match_sc_t.group(1))) 

                    # Priority 1: Leading number prefix (using existing extract_number_prefix)
                    prefix_num = extract_number_prefix(filename)
                    if prefix_num != float('inf'):
                        return (1, prefix_num)
                    
                    # Priority 2: Fallback to filename for alphabetical sort (case-insensitive)
                    return (2, filename.lower())

                audio_files_sorted = sorted(raw_audio_files, key=get_sort_key_for_problematic)
            else:
                # Original logic for non-problematic lessons (alphabetical sort as per existing code)
                logger.info(f"Applying default alphabetical sorting for non-problematic lesson: '{lesson_title}' (index {lesson_index})")
                audio_files_sorted = sorted(raw_audio_files)
            
            audio_files = audio_files_sorted

            if audio_files:
                try:
                    await context.bot.send_message(chat_id=user_id, text=f"'{lesson_title}' сабағының материалдары жіберілуде...", protect_content=True)
                except NetworkError as e:
                    logger.error(f"Network error sending 'materials sending' message in select_lesson: {e}", exc_info=True)
                
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
                    except NetworkError as e_send_audio_net:
                        logger.error(f"Network error sending audio file {audio_file_path} to user {user_id}: {e_send_audio_net}", exc_info=True)
                        try:
                            await context.bot.send_message(chat_id=user_id, text=f"'{audio_file_name}' файлын жіберу кезінде желі қатесі орын алды.", protect_content=True)
                        except NetworkError as e_inner:
                            logger.error(f"Network error sending audio send error message: {e_inner}", exc_info=True)
                    except Exception as e_send_audio:
                        logger.error(f"Failed to send audio file {audio_file_path} to user {user_id}: {e_send_audio}", exc_info=True)
                        try:
                            await context.bot.send_message(chat_id=user_id, text=f"'{audio_file_name}' файлын жіберу кезінде қате орын алды.", protect_content=True)
                        except NetworkError as e_inner:
                            logger.error(f"Network error sending audio send generic error message: {e_inner}", exc_info=True)
                try:
                    await context.bot.send_message(chat_id=user_id, text=f"'{lesson_title}' сабағының барлық материалдары жіберілді.", protect_content=True)
                except NetworkError as e:
                    logger.error(f"Network error sending 'all materials sent' message: {e}", exc_info=True)
            else:
                logger.info(f"No audio files found in {lesson_folder_path}.")
                try:
                    await context.bot.send_message(chat_id=user_id, text=f"'{lesson_title}' сабағы үшін аудио материалдар әзірге жоқ немесе табылмады.", protect_content=True)
                except NetworkError as e:
                    logger.error(f"Network error sending 'no audio materials' message: {e}", exc_info=True)
        else:
            logger.warning(f"Lesson folder not found: {lesson_folder_path}")
            try:
                await context.bot.send_message(chat_id=user_id, text=f"'{lesson_title}' сабағының материалдары табылмады. Әкімшіге хабарласыңыз.", protect_content=True)
            except NetworkError as e:
                logger.error(f"Network error sending 'lesson folder not found' message: {e}", exc_info=True)

    except psycopg2.Error as e_db:
        logger.error(f"Database error in select_lesson for user {user_id}, lesson '{lesson_title}': {e_db}", exc_info=True)
        # query.answer() уже был вызван
        try:
            await context.bot.send_message(chat_id=user_id, text="Дерекқор қатесі орын алды. Әкімшіге хабарласыңыз.", protect_content=True)
        except NetworkError as e_net:
            logger.error(f"Network error sending DB error in select_lesson: {e_net}", exc_info=True)
        conn.rollback()
    except Exception as e_generic:
        logger.error(f"Unexpected error in select_lesson for user {user_id}, lesson '{lesson_title}': {e_generic}", exc_info=True)
        # query.answer() уже был вызван
        try:
            await context.bot.send_message(chat_id=user_id, text="Белгісіз қате орын алды. Әкімшіге хабарласыңыз.", protect_content=True)
        except NetworkError as e_net:
            logger.error(f"Network error sending generic error in select_lesson: {e_net}", exc_info=True)

# Обработчик команды /approve (для обратной совместимости)
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) not in ADMIN_IDS:
        try:
            await update.message.reply_text("Бұл команда тек әкімшіге арналған.", protect_content=True)
        except NetworkError as e:
            logger.error(f"Network error in legacy /approve (auth): {e}", exc_info=True)
        return
    try:
        user_id = int(context.args[0])
        logger.info(f"Legacy /approve command for user_id: {user_id}")
        payment_date = datetime.now()
        expiry_date = payment_date + timedelta(days=365) # 12 месяцев
        cur.execute(
            "UPDATE users SET status = %s, payment_date = %s, expiry_date = %s WHERE user_id = %s",
            ('approved', payment_date, expiry_date, user_id)
        )
        conn.commit()
        logger.info(f"User {user_id} approved via legacy /approve.")

        reply_markup = create_lesson_keyboard()
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"""✅ Төлем расталды! Сабақтарға қол жеткізу ашылды (legacy /approve арқылы).
Мерзімі: {expiry_date.strftime('%d.%m.%Y')} дейін.
Төмендегі сабақтарды таңдаңыз:""",
                reply_markup=reply_markup,
                protect_content=True
            )
        except NetworkError as e:
            logger.error(f"Network error sending approval message in legacy /approve to user {user_id}: {e}", exc_info=True)
        
        try:
            await update.message.reply_text(f"Қол жеткізу ID: {user_id} үшін ашылды (legacy /approve).", protect_content=True)
        except NetworkError as e:
            logger.error(f"Network error sending confirmation message in legacy /approve to admin: {e}", exc_info=True)

    except (IndexError, ValueError):
        try:
            await update.message.reply_text("Пайдалану: /approve <user_id>", protect_content=True)
        except NetworkError as e:
            logger.error(f"Network error sending usage message in legacy /approve: {e}", exc_info=True)
    except psycopg2.Error as e_db:
        logger.error(f"Database error in legacy /approve for user_id {context.args[0] if context.args else 'N/A'}: {e_db}", exc_info=True)
        conn.rollback()
        try:
            await update.message.reply_text("База данных қатесі (/approve). Әкімшіге хабарласыңыз.", protect_content=True)
        except NetworkError as e:
            logger.error(f"Network error sending DB error message in legacy /approve: {e}", exc_info=True)
    except Exception as e_generic:
        logger.error(f"Unexpected error in legacy /approve for user_id {context.args[0] if context.args else 'N/A'}: {e_generic}", exc_info=True)
        try:
            await update.message.reply_text("Белгісіз қате орын алды (/approve).", protect_content=True)
        except NetworkError as e:
            logger.error(f"Network error sending generic error message in legacy /approve: {e}", exc_info=True)

# Обработчик команды /reject (для обратной совместимости)
async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) not in ADMIN_IDS:
        try:
            await update.message.reply_text("Бұл команда тек әкімшіге арналған.", protect_content=True)
        except NetworkError as e:
            logger.error(f"Network error in legacy /reject (auth): {e}", exc_info=True)
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

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Төлем расталмады (legacy /reject арқылы). Қайта тексеріп, чекті қайта жіберіңіз.",
                protect_content=True
            )
        except NetworkError as e:
            logger.error(f"Network error sending rejection message in legacy /reject to user {user_id}: {e}", exc_info=True)
        
        try:
            await update.message.reply_text(f"Қол жеткізу ID: {user_id} үшін жабылды (legacy /reject).", protect_content=True)
        except NetworkError as e:
            logger.error(f"Network error sending confirmation message in legacy /reject to admin: {e}", exc_info=True)

    except (IndexError, ValueError):
        try:
            await update.message.reply_text("Пайдалану: /reject <user_id>", protect_content=True)
        except NetworkError as e:
            logger.error(f"Network error sending usage message in legacy /reject: {e}", exc_info=True)
    except psycopg2.Error as e_db:
        logger.error(f"Database error in legacy /reject for user_id {context.args[0] if context.args else 'N/A'}: {e_db}", exc_info=True)
        conn.rollback()
        try:
            await update.message.reply_text("База данных қатесі (/reject). Әкімшіге хабарласыңыз.", protect_content=True)
        except NetworkError as e:
            logger.error(f"Network error sending DB error message in legacy /reject: {e}", exc_info=True)
    except Exception as e_generic:
        logger.error(f"Unexpected error in legacy /reject for user_id {context.args[0] if context.args else 'N/A'}: {e_generic}", exc_info=True)
        try:
            await update.message.reply_text("Белгісіз қате орын алды (/reject).", protect_content=True)
        except NetworkError as e:
            logger.error(f"Network error sending generic error message in legacy /reject: {e}", exc_info=True)

# Команда для связи с администратором (Администраторға хабарласу)
async def contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    user_name = user.full_name

    # Проверяем, есть ли текст после команды
    if not context.args:
        try:
            await update.message.reply_text(
                "📞 Әкімшіге хабарлама жіберу үшін команданы келесі түрде пайдаланыңыз:\n\n"
                "🔸 /admin_khabar Сіздің хабарламаңыз\n"
                "🔸 /contact_admin Сіздің хабарламаңыз\n\n"
                "📝 Мысал:\n"
                "/admin_khabar Сабақтар ашылмай тұр\n"
                "/contact_admin Төлем туралы сұрағым бар\n\n"
                "⚠️ Команда мен хабарламаның арасында бос орын қалдырыңыз!",
                protect_content=True
            )
        except NetworkError as e:
            logger.error(f"Network error in contact_admin sending usage info: {e}", exc_info=True)
        return

    # Объединяем все аргументы в одно сообщение
    message_text = ' '.join(context.args)

    # Отправляем сообщение администраторам
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"📨 Жаңа хабарлама пайдаланушыдан:\n\n"
                     f"👤 Пайдаланушы: {user_name}\n"
                     f"🆔 ID: {user_id}\n"
                     f"💬 Хабарлама: {message_text}\n\n"
                     f"📤 Жауап беру үшін: /reply {user_id} жауап_мәтіні",
                protect_content=True
            )
            logger.info(f"User message sent to admin {admin_id} from user {user_id}")
        except (NetworkError, TelegramError) as e:
            logger.error(f"Error sending user message to admin {admin_id}: {e}", exc_info=True)

    # Подтверждаем пользователю
    try:
        await update.message.reply_text(
            "✅ Сіздің хабарламаңыз әкімшіге жіберілді!\n"
            "⏳ Жауапты күтіңіз.",
            protect_content=True
        )
    except NetworkError as e:
        logger.error(f"Network error sending confirmation to user in contact_admin: {e}", exc_info=True)

# Команда для ответа админа пользователю
async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, что это админ
    if str(update.message.from_user.id) not in ADMIN_IDS:
        try:
            await update.message.reply_text("Бұл команда тек әкімшіге арналған.", protect_content=True)
        except NetworkError as e:
            logger.error(f"Network error in reply_to_user sending auth error: {e}", exc_info=True)
        return

    # Проверяем формат команды: /reply user_id текст ответа
    if len(context.args) < 2:
        try:
            await update.message.reply_text(
                "Пайдалану: /reply <user_id> <жауап мәтіні>\n"
                "Мысал: /reply 123456789 Сіздің мәселеңіз шешілді",
                protect_content=True
            )
        except NetworkError as e:
            logger.error(f"Network error in reply_to_user sending usage info: {e}", exc_info=True)
        return

    try:
        # Извлекаем user_id и текст ответа
        user_id = int(context.args[0])
        reply_text = ' '.join(context.args[1:])

        # Отправляем ответ пользователю
        await context.bot.send_message(
            chat_id=user_id,
            text=f"Әкімшіден жауап:\n\n{reply_text}",
            protect_content=True
        )

        # Подтверждаем админу
        try:
            await update.message.reply_text(
                f"Жауап пайдаланушыға жіберілді (ID: {user_id})",
                protect_content=True
            )
        except NetworkError as e:
            logger.error(f"Network error sending confirmation to admin in reply_to_user: {e}", exc_info=True)

        logger.info(f"Admin {update.message.from_user.id} sent reply to user {user_id}: {reply_text}")

    except ValueError:
        try:
            await update.message.reply_text(
                "Қате: user_id сан болуы керек\n"
                "Мысал: /reply 123456789 Сіздің жауабыңыз",
                protect_content=True
            )
        except NetworkError as e:
            logger.error(f"Network error sending ValueError message in reply_to_user: {e}", exc_info=True)
    except (NetworkError, TelegramError) as e:
        logger.error(f"Error sending reply to user {context.args[0] if context.args else 'N/A'}: {e}", exc_info=True)
        try:
            await update.message.reply_text(
                "Жауапты жіберу кезінде қате орын алды. Пайдаланушы ID дұрыс екенін тексеріңіз.",
                protect_content=True
            )
        except NetworkError as ne:
            logger.error(f"Network error sending error message in reply_to_user: {ne}", exc_info=True)

# Команда для просмотра запросов (Сұраныстарды қарау)
async def view_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, что это админ
    if str(update.message.from_user.id) not in ADMIN_IDS:
        try:
            await update.message.reply_text("❌ Бұл команда тек әкімшіге арналған.", protect_content=True)
        except NetworkError as e:
            logger.error(f"Network error in view_requests sending auth error: {e}", exc_info=True)
        return

    try:
        await update.message.reply_text(
            "📋 Сұраныстарды қарау командалары:\n\n"
            "🔸 /view_requests - Осы анықтама\n"
            "🔸 /suranys_karu - Осы анықтама (қазақша)\n"
            "🔸 /reply <user_id> <жауап> - Пайдаланушыға жауап беру\n\n"
            "📝 Жауап беру мысалы:\n"
            "/reply 123456789 Сіздің мәселеңіз шешілді\n\n"
            "ℹ️ Пайдаланушылардан келген хабарламалар автоматты түрде сізге жіберіледі.\n"
            "Әр хабарламада пайдаланушының ID көрсетіледі - оны /reply командасында пайдаланыңыз.",
            protect_content=True
        )
    except NetworkError as e:
        logger.error(f"Network error in view_requests: {e}", exc_info=True)

# Основная функция
def main():
    try:
        # Создаем приложение и добавляем обработчики
        application = Application.builder().token(TOKEN).connect_timeout(60).read_timeout(60).write_timeout(60).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(next_step, pattern='next'))
        application.add_handler(CallbackQueryHandler(button, pattern='start'))
        application.add_handler(CallbackQueryHandler(get_access, pattern='get_access'))

        # Команды для связи с администратором (казахские и английские варианты)
        application.add_handler(CommandHandler("admin_khabar", contact_admin))  # Администраторға хабарласу
        application.add_handler(CommandHandler("contact_admin", contact_admin))  # English version

        # Команды для просмотра запросов админом
        application.add_handler(CommandHandler("suranys_karu", view_requests))  # Сұраныстарды қарау
        application.add_handler(CommandHandler("view_requests", view_requests))  # English version

        # Команда для ответа админа пользователю
        application.add_handler(CommandHandler("reply", reply_to_user))

        # Обработчик сообщений должен быть в конце, чтобы не перехватывать команды
        application.add_handler(MessageHandler(filters.PHOTO | filters.Document.PDF | filters.Document.IMAGE, handle_payment))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment))
        
        # Существующие обработчики
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
    # Инициализация настроек
    load_video_file_id()
    main()
