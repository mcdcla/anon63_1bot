import telebot
import time
import random
import string
from datetime import datetime, timezone
from telebot import types

# --- Токены ---
BOT_TOKEN = "7413834924:AAEqqeIU8XnkYzCIW0noJrhr_fKFzbTFoZI"
DEVELOPER_TOKEN = "3d806cz78"

# --- Константы ---
LEAVE_RANK_BLOCK_TIME = 240  # Часов блокировки после снятия с должности
INVALID_TOKEN_BLOCK_TIME = 240  # Часов блокировки за неверный токен
ADMIN_TOKEN_BLOCK_TIME = 120 # Часов блокировки после использования неверного токена администратора

# --- Глобальные переменные ---
bot = telebot.TeleBot(BOT_TOKEN)
users = {}  # Словарь для хранения информации о пользователях
admins = {} # Словарь для хранения администраторов
manager = None # Переменная для хранения менеджера
admin_tokens = {}  # Словарь для хранения токенов администраторов
is_moderating = {} # Модерация сообщений
known_users = [] # список зарегестрированных пользователей

# --- Функции управления ролями ---
def is_admin(user_id):
    return user_id in admins

def is_manager(user_id):
    return users.get(user_id, {}).get('role') == 'manager'

def send_moderation_message(user_id, message, admin_id):
    """Отправляет сообщение на модерацию администраторам/менеджерам."""
    user = users.get(user_id)
    if not user:
        return

    if not is_moderating.get(admin_id, False):
        return

    username = user['username']
    first_name = user['name']
    user_link = f"tg://user?id={user_id}"

    message_text = f"<a href=\"{user_link}\">{first_name}</a>, ID: {user_id}"
    bot.send_message(admin_id, message_text, parse_mode="HTML")

    if message.content_type == 'text':
        bot.send_message(admin_id, message.text)
    elif message.content_type == 'photo':
        bot.send_photo(admin_id, message.photo[-1].file_id, caption=message.caption)
    elif message.content_type == 'video':
        bot.send_video(admin_id, message.video.file_id, caption=message.caption)
    elif message.content_type == 'audio':
        bot.send_audio(admin_id, message.audio.file_id, caption=message.caption)
    elif message.content_type == 'document':
        bot.send_document(admin_id, message.document.file_id, caption=message.caption)
    elif message.content_type == 'sticker':
        bot.send_sticker(admin_id, message.sticker.file_id)
    elif message.content_type == 'location':
        bot.send_location(admin_id, message.location.latitude, message.location.longitude)
    elif message.content_type == 'contact':
        bot.send_contact(admin_id, message.contact.phone_number, message.contact.first_name, last_name=message.contact.last_name)
    elif message.content_type == 'voice':
        bot.send_voice(admin_id, message.voice.file_id, caption=message.caption)
    else:
        bot.send_message(admin_id, "Тип контента не поддерживается.")

    # Inline keyboard for moderators
    keyboard = types.InlineKeyboardMarkup()
    stop_moderation_button = types.InlineKeyboardButton(text="Остановить модерацию⛔️", callback_data="stop_moderation")
    keyboard.add(stop_moderation_button)
    bot.send_message(admin_id, "Для остановки приёмки сообщений также к сообщению будет привязана кнопка \"Остановить модерацию⛔️\"", reply_markup=keyboard)

def send_message_to_admins_managers(sender_id, message): # Отправка сообщений админам
    """Отправляет сообщение от администратора/менеджера другим администраторам/менеджерам."""

    for user_id, user_data in users.items():
        if (is_admin(user_id) or is_manager(user_id)) and user_id != sender_id:
            if is_manager(sender_id):
                sender_name = users[sender_id]['name']
                message_text = f"Сообщение от {sender_name}:"
            else:
                message_text = "Сообщение от Неизвестен:"

            bot.send_message(user_id, message_text)

            if message.content_type == 'text':
                bot.send_message(user_id, message.text)
            elif message.content_type == 'photo':
                bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption)
            elif message.content_type == 'video':
                bot.send_video(user_id, message.video.file_id, caption=message.caption)
            elif message.content_type == 'audio':
                bot.send_audio(user_id, message.audio.file_id, caption=message.caption)
            elif message.content_type == 'document':
                bot.send_document(user_id, message.document.file_id, caption=message.caption)
            elif message.content_type == 'sticker':
                bot.send_sticker(user_id, message.sticker.file_id)
            elif message.content_type == 'location':
                bot.send_location(user_id, message.location.latitude, message.location.longitude)
            elif message.content_type == 'contact':
                bot.send_contact(user_id, message.contact.phone_number, message.contact.first_name, last_name=message.contact.last_name)
            elif message.content_type == 'voice':
                bot.send_voice(user_id, message.voice.file_id, caption=message.caption)
            else:
                bot.send_message(user_id, "Тип контента не поддерживается.")

def send_panel(user_id): # Вывод панели управления

    markup = types.InlineKeyboardMarkup(row_width=1)
    item1 = types.InlineKeyboardButton("Модерация сообщений📰", callback_data='start_moderate')
    item2 = types.InlineKeyboardButton("Написать сообщение✍️", callback_data='send_message')

    if is_manager(user_id):
        item3 = types.InlineKeyboardButton("Администрация🧑‍💻", callback_data='admin_management')
        markup.add(item1, item2, item3)
    elif is_admin(user_id):
        markup.add(item1, item2)

    bot.send_message(user_id, "Панель управления", reply_markup=markup)

def generate_token(length=14):
    """Генерирует случайный токен."""
    characters = string.ascii_letters + string.digits
    token = ''.join(random.choice(characters) for i in range(length))
    return token

def clear_chat(chat_id):
    """Очищает историю чата с ботом."""
    try:
        # Get the last message's ID
        message_id = bot.get_chat_history(chat_id, limit=1)[0].message_id
        # Delete messages up to the last received
        for i in range(message_id, 0, -1):
            try:
                bot.delete_message(chat_id, i)
            except Exception as e:
                # If message doesn't exist or bot can't delete it
                print(f"Error deleting message {i}: {e}")
                break
            time.sleep(0.1)  # Add a delay to avoid hitting rate limits
    except Exception as e:
        print(f"Error clearing chat: {e}")

# --- Клавиатуры ---
def create_stop_moderation_keyboard():
    """Создает клавиатуру для остановки модерации."""
    keyboard = types.InlineKeyboardMarkup()
    stop_button = types.InlineKeyboardButton(text="Остановить модерацию⛔️", callback_data="stop_moderation")
    keyboard.add(stop_button)
    return keyboard

def create_admin_list_keyboard():
    """Создает клавиатуру со списком администраторов."""
    markup = types.InlineKeyboardMarkup()
    for admin_id, admin_data in admins.items():
        username = users[admin_id]['username']
        first_name = users[admin_id]['name']
        markup.add(types.InlineKeyboardButton(text=first_name, callback_data=f'admin_profile_{admin_id}'))
    markup.add(types.InlineKeyboardButton(text="Добавить администратора➕", callback_data='add_admin'))
    markup.add(types.InlineKeyboardButton(text="Назад", callback_data='back_to_panel'))
    return markup

def create_admin_profile_keyboard(admin_id):
    """Создает клавиатуру для профиля администратора."""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="Снять с должности♿️", callback_data=f'remove_admin_{admin_id}'))
    markup.add(types.InlineKeyboardButton(text="Назад", callback_data='admin_management'))
    return markup

def create_copy_token_keyboard(token):
    """Создает кнопку для копирования токена."""
    markup = types.InlineKeyboardMarkup()
    copy_button = types.InlineKeyboardButton(text="Скопировать📑", callback_data=f'copy_token_{token}')
    markup.add(copy_button)
    markup.add(types.InlineKeyboardButton(text="Назад", callback_data='back_to_panel'))
    return markup

# --- Обработчики команд ---

@bot.message_handler(commands=['start'])
def start(message):
    """Обработчик команды /start."""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name


    if user_id not in users:
        users[user_id] = {'username': username, 'name': first_name, 'role': 'user', 'blocked_until': 0, 'admin_since': None}
        known_users.append(user_id) # Запоминаем пользователя который ввел команду /start
        bot.send_message(user_id, "Отправьте Ваше сообщение или любой другой вид информации")
    elif users[user_id]['admin_since'] != None or users[user_id]['role'] == 'manager':
        send_panel(user_id) # Открывает панель управления, если пользователь взаимодействовал с ботом и является админом или менеджером
    else:
        bot.send_message(user_id, "Отправьте Ваше сообщение или любой другой вид информации")

@bot.message_handler(commands=['menu'])
def menu(message): # Вызов панели
    user_id = message.from_user.id

    if not (is_admin(user_id) or is_manager(user_id)):
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return

    send_panel(user_id)

@bot.message_handler(commands=['manager_token'])
def manager_token_handler(message):
    """Обработчик для получения роли менеджера."""
    user_id = message.from_user.id

    # Игнорируем команду, если пользователь уже авторизован
    if is_manager(user_id) or is_admin(user_id):
        bot.reply_to(message, "Вы уже авторизованы как администратор/менеджер.")
        return

    bot.reply_to(message, "Send token")
    bot.register_next_step_handler(message, process_manager_token)

def process_manager_token(message):
    """Проверяет токен менеджера."""
    user_id = message.from_user.id
    token = message.text

    if token == DEVELOPER_TOKEN:
        users[user_id]['role'] = 'manager'
        username = users[user_id]['username']
        first_name = users[user_id]['name']
        admins[user_id] = {'name': first_name, 'link': username, 'since': int(time.time())}
        bot.reply_to(message, "The manager has successfully entered")
        send_panel(user_id)
    else:
        users[user_id]['blocked_until'] = time.time() + INVALID_TOKEN_BLOCK_TIME * 3600
        bot.reply_to(message, f"Неверный токен. Вы заблокированы на {INVALID_TOKEN_BLOCK_TIME} часов.")

@bot.message_handler(commands=['admin_token'])
def admin_token_handler(message):
    """Обработчик для получения роли администратора."""
    user_id = message.from_user.id

     # Игнорируем команду, если пользователь уже авторизован
    if is_manager(user_id) or is_admin(user_id):
        bot.reply_to(message, "Вы уже авторизованы как администратор/менеджер.")
        return

    bot.reply_to(message, "Send token")
    bot.register_next_step_handler(message, process_admin_token)

def process_admin_token(message):
    """Проверяет токен администратора."""
    user_id = message.from_user.id
    token = message.text

    if token in admin_tokens and admin_tokens[token] == user_id:
        del admin_tokens[token] # Delete token after use
        users[user_id]['role'] = 'admin'
        users[user_id]['admin_since'] = time.time()
        username = users[user_id]['username']
        first_name = users[user_id]['name']
        admins[user_id] = {'name': first_name, 'link': username, 'since': int(time.time())}
        bot.reply_to(message, "The admin has successfully entered")
        send_panel(user_id)
    else:
        users[user_id]['blocked_until'] = time.time() + ADMIN_TOKEN_BLOCK_TIME * 3600
        bot.reply_to(message, f"Неверный токен. Вы заблокированы на {ADMIN_TOKEN_BLOCK_TIME} часов.")

@bot.message_handler(commands=['block'])
def block_user_handler(message):
    "Блокировка пользователя"
    user_id = message.from_user.id

    if not (is_admin(user_id) or is_manager(user_id)):
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return

    try:
        user_id_to_block = int(message.text.split('_')[1])
        block_hours = int(message.text.split('_')[2])
    except (IndexError, ValueError):
        bot.reply_to(message, "Неверный формат команды. Используйте: /block_[id пользователя]_[кол-во часов в блокировке]")
        return

    if user_id_to_block not in users:
        bot.reply_to(message, "Пользователь с таким ID не найден.")
        return

    users[user_id_to_block]['blocked_until'] = time.time() + block_hours * 3600

    username = users[user_id_to_block]['username']
    first_name = users[user_id_to_block]['name']
    user_link = f"tg://user?id={user_id_to_block}"

    bot.reply_to(message, f"Пользователь <a href=\"{user_link}\">{first_name}</a> заблокирован✅", parse_mode="HTML")

@bot.message_handler(commands=['unblock'])
def unblock_user_handler(message):
    """Разблокировка пользователя."""
    user_id = message.from_user.id

    if not (is_admin(user_id) or is_manager(user_id)):
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return

    try:
        user_id_to_unblock = int(message.text.split('_')[1])
    except (IndexError, ValueError):
        bot.reply_to(message, "Неверный формат команды. Используйте: /unblock_[id пользователя]")
        return

    if user_id_to_unblock not in users:
        bot.reply_to(message, "Пользователь с таким ID не найден.")
        return

    users[user_id_to_unblock]['blocked_until'] = 0  # Снимаем блокировку

    username = users[user_id_to_unblock]['username']
    first_name = users[user_id_to_unblock]['name']
    user_link = f"tg://user?id={user_id_to_unblock}"

    bot.reply_to(message, f"Пользователь <a href=\"{user_link}\">{first_name}</a> разблокирован✅", parse_mode="HTML")

@bot.message_handler(commands=['def_on'])
def def_on_handler(message):
    """Переключает администратора/менеджера в режим обычного пользователя."""
    user_id = message.from_user.id
    if not (is_admin(user_id) or is_manager(user_id)):
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return

    # Delete the admin role without touching blocked_until time
    clear_chat(message.chat.id) # Clears chats both sides
    users[user_id]['role'] = 'user'
    users[user_id]['admin_since'] = None # resets "admin since" time
    admins.pop(user_id, None)

    start(message) # resets to /start

@bot.message_handler(commands=['def_off'])
def def_off_handler(message):
    """Переключает администратора/менеджера обратно в административный режим."""
    user_id = message.from_user.id
    if not (is_admin(user_id) or is_manager(user_id)):
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return

    clear_chat(message.chat.id)
    send_panel(user_id)

@bot.message_handler(commands=['leave_rank'])
def leave_rank_handler(message):
    """Позволяет администратору/менеджеру снять себя с должности."""
    user_id = message.from_user.id

    if not (is_admin(user_id) or is_manager(user_id)):
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return

    users[user_id]['role'] = 'user'
    users[user_id]['blocked_until'] = time.time() + LEAVE_RANK_BLOCK_TIME * 3600  # Блокировка команды на 240 часов
    users[user_id]['admin_since'] = None
    admins.pop(user_id, None) # remove from admins dict

    clear_chat(message.chat.id)
    bot.send_message(user_id, f"Вы сняты с должности. Команды администратора будут недоступны в течение {LEAVE_RANK_BLOCK_TIME} часов.")
    start(message)

@bot.message_handler(commands=['admin_add'])
def admin_add_handler(message):
    """Назначает пользователя администратором (только для менеджеров)."""
    user_id = message.from_user.id

    if not is_manager(user_id):
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return

    try:
        user_id_to_promote = int(message.text.split(' ')[1])
    except (IndexError, ValueError):
        bot.reply_to(message, "Неверный формат команды. Используйте: /admin_add [id пользователя]")
        return

    if user_id_to_promote not in users:
        bot.reply_to(message, "Пользователь с таким ID не найден.")
        return

    users[user_id_to_promote]['role'] = 'admin'
    users[user_id_to_promote]['admin_since'] = time.time()
    username = users[user_id_to_promote]['username']
    first_name = users[user_id_to_promote]['name']
    admins[user_id_to_promote] = {'name': first_name, 'link': username, 'since': int(time.time())} # Add to admins dict

    bot.send_message(user_id_to_promote, "Вам назначены права администратора. Используйте /menu для доступа к панели управления.")
    bot.reply_to(message, f"Пользователю {first_name} назначены права администратора.")


@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'audio', 'document', 'sticker', 'location', 'contact', 'voice'])
def echo_all(message):
    user_id = message.from_user.id

    if user_id not in users:
        start(message)
        return

    if users[user_id]['blocked_until'] > time.time():
        bot.reply_to(message, "Вы заблокированы.")
        return

    if users[user_id]['role'] == 'user':
        bot.reply_to(message, "Ваше сообщение доставлено")
        # Отправка на модерацию всем админам и менеджерам
        for admin_id in admins:
            send_moderation_message(user_id, message, admin_id)
        for manager_id, manager_data in users.items():
                if is_manager(manager_id):
                    send_moderation_message(user_id, message, manager_id)

    elif is_manager(user_id) or is_admin(user_id):
        # Message from admin/manager
        send_message_to_admins_managers(user_id, message)
        bot.reply_to(message, "Ваше сообщение доставлено")

# --- Callback Query Handlers ---

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if call.data == 'start_moderate':
        # Логика начала модерации сообщений
        if is_admin(user_id) or is_manager(user_id):
            if not is_moderating.get(chat_id, False):
                is_moderating[chat_id] = True
                bot.send_message(user_id, "Вы начали модерацию сообщений. Сообщения от пользователей будут пересылаться вам.", reply_markup=create_stop_moderation_keyboard())
            else:
                bot.send_message(user_id, "Вы уже модерируете сообщения.")
        else:
            bot.answer_callback_query(call.id, "У вас нет прав для модерации.")

    elif call.data == 'stop_moderation':
        # Логика остановки модерации сообщений
        if is_admin(user_id) or is_manager(user_id):
            if is_moderating.get(chat_id, False):
                is_moderating[chat_id] = False
                bot.send_message(user_id, "Вы остановили модерацию сообщений.")
                send_panel(user_id)  # Возврат в панель управления
            else:
                bot.send_message(user_id, "Вы не модерируете сообщения в данный момент.")
        else:
            bot.answer_callback_query(call.id, "У вас нет прав для остановки модерации.")

    elif call.data == 'send_message':
        bot.send_message(user_id, "Введите Ваше сообщение")
        bot.register_next_step_handler(call.message, process_admin_message)

    elif call.data == 'admin_management':
        bot.edit_message_text("Администраторы:", user_id, call.message.message_id, reply_markup=create_admin_list_keyboard())

    elif call.data.startswith('admin_profile_'):
        admin_id = int(call.data[len('admin_profile_'):])
        admin_info = admins[admin_id]
        # Format the admin info
        username = users[admin_id]['username']
        first_name = users[admin_id]['name']
        admin_user_link = f"tg://user?id={admin_id}"
        since_date = datetime.fromtimestamp(users[admin_id]['admin_since'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC') # Getting admin_since from users list instead admins list

        message_text = (
            f"Это 🪪<a href=\"{admin_user_link}\">{first_name}</a>\n"
            f"ID: {admin_id}\n"
            f"Работает с ⏱️{since_date}"
        )

        bot.edit_message_text(message_text, user_id, call.message.message_id, reply_markup=create_admin_profile_keyboard(admin_id), parse_mode="HTML")

    elif call.data == 'add_admin':
        token = generate_token()
        admin_tokens[token] = user_id  # Store token for user
        bot.send_message(user_id, f"Токен для активации прав администратора: {token}", reply_markup=create_copy_token_keyboard(token))
        bot.answer_callback_query(call.id, "Токен сгенерирован и отправлен.")
        send_panel(user_id)

    elif call.data == 'back_to_panel':
        send_panel(user_id)

    elif call.data.startswith('remove_admin_'):
        admin_id_to_remove = int(call.data[len('remove_admin_'):])
        # Getting profile info to send confirmation message
        username = users[admin_id_to_remove]['username']
        first_name = users[admin_id_to_remove]['name']
        admin_user_link = f"tg://user?id={admin_id_to_remove}"
        # Remove admin
        users[admin_id_to_remove]['role'] = 'user'
        users[admin_id_to_remove]['admin_since'] = None
        admins.pop(admin_id_to_remove, None)

        bot.answer_callback_query(call.id, f"Администратор 🪪<a href=\"{admin_user_link}\">{first_name}</a> был снят с должности.", parse_mode="HTML")
        bot.send_message(user_id, f"Администратор 🪪<a href=\"{admin_user_link}\">{first_name}</a> был снят с должности.", parse_mode="HTML")
        bot.edit_message_text("Администраторы:", user_id, call.message.message_id, reply_markup=create_admin_list_keyboard())

    elif call.data.startswith('copy_token_'):
        token = call.data[len('copy_token_'):]
        bot.answer_callback_query(call.id, f"Токен скопирован: {token}")
        send_panel(user_id)
    else:
        bot.answer_callback_query(call.id, "Действие не поддерживается.")

def process_admin_message(message):
    """Обрабатывает сообщение, отправленное администратором/менеджером."""
    user_id = message.from_user.id

    # Отправляем сообщение всем админам и менеджерам, кроме отправителя
    send_message_to_admins_managers(user_id, message)

    bot.reply_to(message, "Ваше сообщение доставлено другим администраторам/менеджерам.")


# --- Запуск бота ---
if __name__ == '__main__':
    bot.infinity_polling()
