import telebot
import time
import random
import os
from datetime import datetime, timezone

# Замените 'YOUR_BOT_TOKEN' на токен вашего бота
BOT_TOKEN = "7413834924:AAEqqeIU8XnkYzCIW0noJrhr_fKFzbTFoZI"
bot = telebot.TeleBot("7413834924:AAEqqeIU8XnkYzCIW0noJrhr_fKFzbTFoZI")

# Словари и переменные
users = {}  # id: {'role': 'user/manager/admin', 'blocked_until': timestamp, 'admin_since': timestamp, 'username': username, 'name': name}
manager_token = "3d806cz78"
admin_tokens = {}  # token: user_id
admins = {}  # user_id: {'name': str, 'link': str, 'since': timestamp} - информация об администраторах
moderation_queue = {}  # user_id: [message_id1, message_id2, ...]
current_moderator = {} # user_id: True/False
last_message_from = {} # user_id: chat_id
DEFAULT_BLOCK_TIME = 240 # hours
LEAVE_RANK_BLOCK_TIME = 240 # hours
ADMIN_TOKEN_BLOCK_TIME = 120 # hours

# --- Клавиатуры (Inline) ---

def create_main_menu_keyboard():
    """Создает клавиатуру главного меню для менеджера."""
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row_width = 1 # Чтобы кнопки были в столбик
    keyboard.add(
        telebot.types.InlineKeyboardButton("Модерация сообщений📰", callback_data='moderate'),
        telebot.types.InlineKeyboardButton("Написать сообщение✍️", callback_data='send_message'),
        telebot.types.InlineKeyboardButton("Администрация🧑‍💻", callback_data='admin_management')
    )
    return keyboard

def create_admin_menu_keyboard():
    """Создает клавиатуру главного меню для администратора."""
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(
        telebot.types.InlineKeyboardButton("Модерация сообщений📰", callback_data='moderate'),
        telebot.types.InlineKeyboardButton("Написать сообщение✍️", callback_data='send_message')
    )
    return keyboard

def create_admin_list_keyboard():
    """Создает клавиатуру со списком администраторов."""
    keyboard = telebot.types.InlineKeyboardMarkup()
    for admin_id in admins:
        admin_name = admins[admin_id]['name']
        keyboard.add(telebot.types.InlineKeyboardButton(admin_name, callback_data=f'admin_profile_{admin_id}'))

    keyboard.add(telebot.types.InlineKeyboardButton("Добавить администратора➕", callback_data='add_admin')) # кнопка добавления
    keyboard.add(telebot.types.InlineKeyboardButton("Назад", callback_data='back_to_panel')) # кнопка "назад"
    return keyboard

def create_admin_profile_keyboard(admin_id):
    """Создает клавиатуру для профиля администратора."""
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton("Снять с должности♿️", callback_data=f'remove_admin_{admin_id}')) # кнопка удаления
    keyboard.add(telebot.types.InlineKeyboardButton("Назад", callback_data='admin_management'))
    return keyboard

def create_stop_moderation_keyboard():
    """Создает клавиатуру с кнопкой остановки модерации."""
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton("Остановить модерацию⛔️", callback_data='stop_moderation'))
    return keyboard

def create_copy_token_keyboard(token):
     """Создает клавиатуру с кнопкой копирования токена."""
     keyboard = telebot.types.InlineKeyboardMarkup()
     keyboard.add(telebot.types.InlineKeyboardButton("Скопировать📑", callback_data=f'copy_token_{token}'))
     return keyboard

# --- Функции ---

def generate_token():
    """Генерирует случайный токен для администратора."""
    return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=14))

def is_admin(user_id):
    """Проверяет, является ли пользователь администратором."""
    return users.get(user_id, {}).get('role') == 'admin'

def is_manager(user_id):
    """Проверяет, является ли пользователь менеджером."""
    return users.get(user_id, {}).get('role') == 'manager'

def send_panel(user_id):
    """Отправляет панель управления в зависимости от роли пользователя."""
    user_role = users.get(user_id, {}).get('role')
    if user_role == 'manager':
        bot.send_message(user_id, "Панель управления", reply_markup=create_main_menu_keyboard())
    elif user_role == 'admin':
        bot.send_message(user_id, "Панель управления", reply_markup=create_admin_menu_keyboard())
    else:
        bot.send_message(user_id, "Команда доступна только для администраторов и распорядителей.")

def clear_chat(chat_id):
    """Удаляет все сообщения бота в чате."""
    try:
        # Получаем последние сообщения в чате
        messages = bot.get_chat_history(chat_id, limit=100)  # Получаем последние 100 сообщений

        # Перебираем сообщения и удаляем их, если они отправлены ботом
        for message in messages:
            if message.from_user.id == bot.get_me().id:
                bot.delete_message(chat_id, message.message_id)
    except Exception as e:
        print(f"Ошибка при очистке чата: {e}")

def block_user(user_id, hours):
    """Блокирует пользователя на указанное количество часов."""

    users[user_id]['blocked_until'] = time.time() + hours * 3600
    bot.send_message(user_id, f"Вы заблокированы на {hours} часов.")

def unblock_user(user_id):
    """Разблокирует пользователя."""
    users[user_id]['blocked_until'] = 0
    bot.send_message(user_id, "Вы разблокированы.")

def send_moderation_message(user_id, message):
    """Отправляет сообщение на модерацию администраторам/менеджерам."""
    for admin_id, admin_data in admins.items():
        if admin_id != user_id:
           try:
              username = users[user_id]['username']
              first_name = users[user_id]['name']
              user_link = f"tg://user?id={user_id}"

              # Send first message: User info
              message1 = f"Сообщение от: 🪪<a href=\"{user_link}\">{first_name}</a>, ID: {user_id}"
              bot.send_message(admin_id, message1, parse_mode="HTML")

              # Send second message: Content
              message2 = f"Содержание сообщения: {message.text}"
              bot.send_message(admin_id, message2)
           except Exception as e:
              print(f"Error sending message to admin {admin_id}: {e}")

    for manager_id, manager_data in users.items():
        if is_manager(manager_id) and manager_id != user_id:
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

# --- Обработчики ---

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    name = message.from_user.first_name

    # Инициализация пользователя, если его нет в базе
    if user_id not in users:
        users[user_id] = {'role': 'user', 'blocked_until': 0, 'admin_since': None, 'username': username, 'name': name}
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
        send_panel(user_id)
    else:
        bot.reply_to(message, "Неверный токен. Вы заблокированы на 240 часов.")
        block_user(user_id, DEFAULT_BLOCK_TIME)

@bot.message_handler(commands=['block'])
def block_user_handler(message):
    """Блокирует пользователя по команде."""
    if not (is_admin(message.from_user.id) or is_manager(message.from_user.id)):
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return

    try:
        parts = message.text.split('_')
        user_id_to_block = int(parts[1])
        block_hours = int(parts[2])
    except (IndexError, ValueError):
        bot.reply_to(message, "Неверный формат команды. Используйте: /block_[id пользователя]_[кол-во часов]")
        return

    if user_id_to_block not in users:
        bot.reply_to(message, "Пользователь с таким ID не найден.")
        return

    # Getting profile info to send confirmation message
    username = users[user_id_to_block]['username']
    first_name = users[user_id_to_block]['name']
    user_link = f"tg://user?id={user_id_to_block}"

    block_user(user_id_to_block, block_hours)
    bot.reply_to(message, f"пользователь 🪪<a href=\"{user_link}\">{first_name}</a> заблокирован✅", parse_mode="HTML")

@bot.message_handler(commands=['unblock'])
def unblock_user_handler(message):
    """Разблокирует пользователя по команде."""
    if not (is_admin(message.from_user.id) or is_manager(message.from_user.id)):
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

     # Getting profile info to send confirmation message
    username = users[user_id_to_unblock]['username']
    first_name = users[user_id_to_unblock]['name']
    user_link = f"tg://user?id={user_id_to_unblock}"

    unblock_user(user_id_to_unblock)
    bot.reply_to(message, f"пользователь 🪪<a href=\"{user_link}\">{first_name}</a> разблокирован✅", parse_mode="HTML")

@bot.message_handler(commands=['def_on'])
def default_on_handler(message):
    """Включает режим обычного пользователя для администратора/менеджера."""
    user_id = message.from_user.id

    if not (is_admin(user_id) or is_manager(user_id)):
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return

    users[user_id]['role'] = 'user'  # понижаем до обычного пользователя
    clear_chat(message.chat.id)
    start(message)

@bot.message_handler(commands=['def_off'])
def default_off_handler(message):
    """Выключает режим обычного пользователя для администратора/менеджера."""
    user_id = message.from_user.id

    if users[user_id]['role'] == 'user':
        if is_admin(user_id):
            users[user_id]['role'] = 'admin'
        elif is_manager(user_id):
            users[user_id]['role'] = 'manager'

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

@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'audio', 'document', 'sticker'])
def echo_all(message):
    user_id = message.from_user.id

    if users[user_id]['blocked_until'] > time.time():
        bot.reply_to(message, "Вы заблокированы.")
        return

    if users[user_id]['role'] == 'user':
        bot.reply_to(message, "Ваше сообщение доставлено")
        send_moderation_message(user_id, message) # Отправка на модерацию
    elif is_manager(user_id) or is_admin(user_id):
        # Message from admin/manager
        for admin_id, admin_data in admins.items():
            if admin_id != user_id:
               try:
                   # Send first message: User info
                   message1 = "Сообщение от: Неизвестен"
                   bot.send_message(admin_id, message1)

                   # Send second message: Content
                   bot.copy_message(admin_id, message.chat.id, message.message_id)
               except Exception as e:
                   print(f"Error sending message to admin {admin_id}: {e}")

        for manager_id, manager_data in users.items():
            if is_manager(manager_id) and manager_id != user_id:
                try:
                    # Send first message: User info
                    message1 = "Сообщение от: Неизвестен"
                    bot.send_message(manager_id, message1)

                    # Send second message: Content
                    bot.copy_message(manager_id, message.chat.id, message.message_id)

                except Exception as e:
                    print(f"Error sending message to manager {manager_id}: {e}")

        bot.reply_to(message, "Ваше сообщение доставлено")

# --- Callback Query Handlers ---

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id

    if call.data == 'moderate':
        # TODO: Реализовать логику модерации сообщений
        bot.answer_callback_query(call.id, "Режим модерации включен.")
    elif call.data == 'send_message':
        bot.send_message(user_id, "Введите Ваше сообщение")
    elif call.data == 'admin_management':
        bot.edit_message_text("Администраторы:", user_id, call.message.message_id, reply_markup=create_admin_list_keyboard())
    elif call.data.startswith('admin_profile_'):
        admin_id = int(call.data[len('admin_profile_'):])
        admin_info = admins[admin_id]

        # Format the admin info
        admin_link = f"tg://user?id={admin_id}"
        since_date = datetime.fromtimestamp(admin_info['since'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

        message_text = (
            f"Это 🪪<a href=\"{admin_link}\">{admin_info['name']}</a>\n"
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

# --- Запуск бота ---
if __name__ == '__main__':
    bot.infinity_polling()
