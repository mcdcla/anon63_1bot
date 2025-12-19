import telebot
import time
import random
import string

# --- Настройки ---
BOT_TOKEN = '7413834924:AAEqqeIU8XnkYzCIW0noJrhr_fKFzbTFoZI'  # Замените на токен вашего бота
manager_token = "3d806cz78" # Замените на ваш токен менеджера
admin_tokens = {} # токен для админа
DEFAULT_BLOCK_TIME = 240 * 3600
ADMIN_TOKEN_BLOCK_TIME = 120 * 3600
bot = telebot.TeleBot(BOT_TOKEN) # Создание бота

# --- Глобальные переменные ---
users = {}
admins = {}
managers = {}

# --- Функции ---

def is_admin(user_id):
    return users.get(user_id, {}).get('role') == 'admin'

def is_manager(user_id):
    return users.get(user_id, {}).get('role') in ['manager', 'admin']

def block_user(user_id, duration):
    users[user_id]['blocked_until'] = time.time() + duration

def generate_token(length=32):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

# --- Клавиатуры ---

def create_panel_keyboard():
    markup = telebot.types.InlineKeyboardMarkup()

    # Модерация есть у всех менеджеров и админов
    moderate_button = telebot.types.InlineKeyboardButton("Модерация сообщений📰", callback_data="moderate")
    write_message_button = telebot.types.InlineKeyboardButton("Написать сообщение✍️", callback_data="send_message")

    markup.add(moderate_button)
    markup.add(write_message_button)

    if is_admin(admin_id): # Только админ может управлять админами
        admin_management_button = telebot.types.InlineKeyboardButton("Управление администраторами⚙️", callback_data="admin_management")
        markup.add(admin_management_button)
    return markup

def create_admin_list_keyboard():
    markup = telebot.types.InlineKeyboardMarkup()
    for admin_id, admin_data in admins.items():
        button_text = f"{admin_data['name']} ({admin_data['link']})"
        callback_data = f"admin_profile_{admin_id}"
        admin_button = telebot.types.InlineKeyboardButton(button_text, callback_data=callback_data)
        markup.add(admin_button)
    add_admin_button = telebot.types.InlineKeyboardButton("Добавить администратора➕", callback_data="add_admin")
    back_button = telebot.types.InlineKeyboardButton("Назад🔙", callback_data="back_to_panel")
    markup.add(add_admin_button,back_button)
    return markup

def create_admin_profile_keyboard(admin_id):
    markup = telebot.types.InlineKeyboardMarkup()
    remove_admin_button = telebot.types.InlineKeyboardButton("Снять с должности⛔️", callback_data=f"remove_admin_{admin_id}")
    back_button = telebot.types.InlineKeyboardButton("Назад🔙", callback_data="admin_management")
    markup.add(remove_admin_button, back_button)
    return markup

def create_stop_moderation_keyboard():
    markup = telebot.types.InlineKeyboardMarkup()
    stop_button = telebot.types.InlineKeyboardButton("Остановить модерацию⛔️", callback_data="stop_moderation")
    markup.add(stop_button)
    return markup

def create_copy_token_keyboard(token):
    markup = telebot.types.InlineKeyboardMarkup()
    copy_button = telebot.types.InlineKeyboardButton("Копировать токен", callback_data=f"copy_token_{token}")
    markup.add(copy_button)
    return markup

# --- Отправка панели управления ---

def send_panel(user_id):
    panel_markup = create_panel_keyboard()  # Теперь не нужны аргументы
    bot.send_message(user_id, "Панель управления:", reply_markup=panel_markup)

# --- Отправка сообщения модераторам ---

def send_moderation_message(user_id, message):
    for manager_id, manager_data in users.items():
        if is_manager(manager_id):
            try:
                username = users[user_id]['username']
                first_name = users[user_id]['name']
                user_link = f"tg://user?id={user_id}"

                # Send first message: User info
                message1 = f"Сообщение от: 🪪<a href=\"{user_link}\">{first_name}</a>, ID: {user_id}"
                bot.send_message(manager_id, message1, parse_mode="HTML")

                # Send second message: Content
                message2 = f"Содержание сообщения: {message.text}"
                bot.send_message(manager_id, message2)
            except Exception as e:
                print(f"Error sending message to manager {manager_id}: {e}")

# Сюда пишем отправку сообщений "как от пользователя" (но с инфой об отправителе)
def send_as_user_message(user_id, message_text):
    try:
        username = users[user_id]['username']
        first_name = users[user_id]['name']
        user_link = f"tg://user?id={user_id}"

        # Send first message: User info
        message1 = f"Сообщение от: 🪪<a href=\"{user_link}\">{first_name}</a>, ID: {user_id}"
        bot.send_message(user_id, message1, parse_mode="HTML")  # Use user_id here

        # Send second message: Content
        message2 = f"Содержание сообщения: {message_text}"
        bot.send_message(user_id, message2)  # Use user_id here
    except Exception as e:
        print(f"Error sending message to user {user_id}: {e}")



# --- Обработчики ---

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    name = message.from_user.first_name

    # Инициализация пользователя, если его нет в базе
    if user_id not in users:
        users[user_id] = {'role': 'user', 'blocked_until': 0, 'admin_since': None, 'username': username, 'name': name, 'moderating': False}
    else:  # Обновление данных, если пользователь уже есть
        users[user_id]['username'] = username
        users[user_id]['name'] = name

    if users[user_id]['blocked_until'] > time.time():
        bot.reply_to(message, "Вы заблокированы.")
        return

    bot.reply_to(message, "Отправьте Ваше сообщение или любой другой вид информации")

    # Дополнительная логика для ролей
    if is_manager(user_id) or is_admin(user_id):
        send_panel(user_id)

@bot.message_handler(commands=['menu'])
def menu(message):
    user_id = message.from_user.id
    if is_manager(user_id):
        send_panel(user_id)
    elif is_admin(user_id):
        send_panel(user_id)
    else:
        bot.send_message(user_id, "Команда доступна только для администраторов и распорядителей.", reply_markup=telebot.types.ReplyKeyboardRemove())

@bot.message_handler(commands=['manager_aut'])
def manager_auth(message):
    user_id = message.from_user.id

    # Проверяем, авторизован ли пользователь
    if users[user_id].get('role') in ['manager', 'admin']:
        bot.reply_to(message, "Вы уже авторизованы.")
        return

    bot.send_message(user_id, "Введите токен:")
    bot.register_next_step_handler(message, process_manager_token)

def process_manager_token(message):
    user_id = message.from_user.id
    token = message.text

    if token == manager_token:
        users[user_id]['role'] = 'manager'
        bot.reply_to(message, "The manager has successfully entered")
        send_panel(user_id)
    else:
        bot.reply_to(message, "Неверный токен. Вы заблокированы на 240 часов.")
        block_user(user_id, DEFAULT_BLOCK_TIME)

@bot.message_handler(commands=['admin_token'])
def admin_auth(message):
    user_id = message.from_user.id

    # Проверяем, авторизован ли пользователь
    if users[user_id].get('role') in ['manager', 'admin']:
        bot.reply_to(message, "Вы уже авторизованы.")
        return

    bot.send_message(user_id, "Введите токен:")
    bot.register_next_step_handler(message, process_admin_token)

def process_admin_token(message):
    user_id = message.from_user.id
    token = message.text

    if token in admin_tokens and admin_tokens[token] == user_id:
        users[user_id]['role'] = 'admin'
        users[user_id]['admin_since'] = time.time()
        admin_id = message.from_user.id
        username = users[message.from_user.id]['username']
        first_name = users[message.from_user.id]['name']
        admins[admin_id] = {'name': first_name, 'link': username, 'since': int(time.time())}

        del admin_tokens[token]
        bot.reply_to(message, "The admin has successfully entered")
        send_panel(message.from_user.id) # Corrected this line

    else:
        bot.reply_to(message, "Неверный токен. Вы заблокированы на 120 часов.")
        block_user(user_id, ADMIN_TOKEN_BLOCK_TIME)

# НОВЫЙ ОБРАБОТЧИК - /admin_add
@bot.message_handler(commands=['admin_add'])
def admin_add(message):
    user_id = message.from_user.id

    # 1. Проверка: Вызывающий команду должен быть администратором
    if not is_admin(user_id): #  Теперь только админ может добавлять админа!
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")
        return

    # 2. Извлечение ID пользователя из аргумента команды
    try:
        user_id_to_add = int(message.text.split()[1])  #  /admin_add 123456789
    except (IndexError, ValueError):
        bot.reply_to(message, "Неверный формат команды. Используйте: /admin_add [ID пользователя Telegram]")
        return

    # 3. Проверка:  Существует ли такой пользователь в принципе (есть ли он в users)
    if user_id_to_add not in users:
        bot.reply_to(message, "Пользователь с таким ID не найден.") # Желательно, чтобы регистрировались все, кто написал /start
        return
    ## 3.1 Проверка, не является ли этот пользователь уже админом
    if users[user_id_to_add]['role'] == 'admin':
        bot.reply_to(message, "Данный пользователь уже является администратором")
        return

    # 4. Добавление пользователя в администраторы
    users[user_id_to_add]['role'] = 'admin'
    users[user_id_to_add]['admin_since'] = time.time() # Можно сохранить время назначения

    # 4.1 Добавляем информацию об админе в admins
    username = users[user_id_to_add]['username']
    first_name = users[user_id_to_add]['name']

    admins[user_id_to_add] = {'name': first_name, 'link': username, 'since': int(time.time())}

    # 5. Отправка подтверждения
    bot.reply_to(message, f"Пользователь с ID {user_id_to_add} добавлен в администраторы.")
    try:
        bot.send_message(user_id_to_add, "Поздравляем, теперь вы администратор!")
        send_panel(user_id_to_add) # Отображаем админ-панель для нового админа
    except telebot.apihelper.ApiException as e:
        if e.result.status_code == 403:
            bot.reply_to(message, f"Не удалось отправить уведомление пользователю {user_id_to_add}, возможно, он заблокировал бота.")
        else:
            print(f"Ошибка при отправке уведомления новому админу: {e}")


@bot.message_handler(func=lambda message: True)
def echo_all(message):
    user_id = message.from_user.id

    if users[user_id]['blocked_until'] > time.time():
        bot.reply_to(message, "Вы заблокированы.")
        return

    # Если пользователь модерирует, то отправляем сообщение ему, а не всем менеджерам.
    if is_manager(user_id) and users[user_id].get('moderating', False):
        send_as_user_message(user_id, message.text)

    else: # Иначе обычная отправка всем менеджерам.
        send_moderation_message(user_id, message)

# --- Callback Handlers ---

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.message:
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        panel_markup = None # Обновим клавиатуру

        if call.data == "moderate":
            users[chat_id]['moderating'] = True  # Включаем режим модерации
            bot.send_message(chat_id, "Ожидайте сообщения для модерации. По окончании нажмите кнопку.", reply_markup=create_stop_moderation_keyboard())

        elif call.data == "send_message":
            bot.send_message(chat_id, "Введите Ваше сообщение")
            bot.register_next_step_handler(call.message, process_manager_message) # Переходим в обработчик сообщений

        elif call.data == "admin_management":
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Список Администраторов", reply_markup=create_admin_list_keyboard())
        elif call.data == "back_to_panel":
            send_panel(chat_id)
        elif call.data == "add_admin":
            # сгенерировать токен
            # записать в словарь admin_tokens
            # отправить токен пользователю
            token = generate_token()
            admin_tokens[token] = chat_id
            bot.send_message(chat_id, f"Ваш токен: {token}", reply_markup=create_copy_token_keyboard(token))
        elif call.data.startswith("admin_profile_"):
            admin_id = call.data.split("_")[2]
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Профиль Администратора", reply_markup=create_admin_profile_keyboard(admin_id))
        elif call.data.startswith("remove_admin_"):
            admin_id = call.data.split("_")[2]
            # снять с должности
            # удалить из списка admins
            if admin_id in admins:
                bot.send_message(chat_id, f"Администратор {admins[admin_id]['name']} снят с должности.")
                del admins[admin_id]
                # TODO: Удалить эту запись и у users[admin_id]
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Список Администраторов", reply_markup=create_admin_list_keyboard())
        elif call.data == "stop_moderation":
            users[chat_id]['moderating'] = False # Выключаем режим модерации
            send_panel(chat_id) # Возвращаемся в панель

        elif call.data.startswith("copy_token_"):
            token = call.data.split("_")[2]
            bot.send_message(chat_id, f"Токен скопирован: {token}")

        if panel_markup is not None: # Обновляем панель управления
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=panel_markup)

# Обработчик сообщений от менеджеров (после нажатия "Написать сообщение")
def process_manager_message(message):
    user_id = message.from_user.id
    send_as_user_message(user_id, message.text)
    bot.send_message(user_id, "Ваше сообщение доставлено")
    send_panel(user_id) # Возвращаемся к панели

print("Бот запущен")
bot.infinity_polling()
