import telebot
import time
import random
import os

# Замените 'YOUR_BOT_TOKEN' на токен вашего бота
BOT_TOKEN = "7413834924:AAEqqeIU8XnkYzCIW0noJrhr_fKFzbTFoZI"
bot = telebot.TeleBot("7413834924:AAEqqeIU8XnkYzCIW0noJrhr_fKFzbTFoZI")

# Словари и переменные
users = {}  # id: {'role': 'user/manager/admin', 'blocked_until': timestamp, 'admin_since': timestamp}
manager_token = "3d806cz78"
admin_tokens = {}  # token: user_id
admins = {}  # user_id: {'name': str, 'link': str, 'since': timestamp} - информация об администраторах 
moderation_queue = {}  # user_id: [message_id1, message_id2, ...]

# Клавиатуры
admin_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
admin_keyboard.add(telebot.types.KeyboardButton("Модерация сообщений📰"))
admin_keyboard.add(telebot.types.KeyboardButton("Написать сообщение✍️"))
admin_keyboard.add(telebot.types.KeyboardButton("/menu"))

manager_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
manager_keyboard.add(telebot.types.KeyboardButton("Модерация сообщений📰"))
manager_keyboard.add(telebot.types.KeyboardButton("Написать сообщение✍️"))
manager_keyboard.add(telebot.types.KeyboardButton("Администрация🧑‍💻"))
manager_keyboard.add(telebot.types.KeyboardButton("/menu"))

user_keyboard = telebot.types.ReplyKeyboardRemove()

moderation_stop_keyboard = telebot.types.InlineKeyboardMarkup()
moderation_stop_keyboard.add(telebot.types.InlineKeyboardButton("Остановить модерацию⛔️", callback_data='stop_moderation'))

def generate_admin_list_keyboard():
    admin_list_keyboard = telebot.types.InlineKeyboardMarkup()
    for admin_id in admins:
        admin_list_keyboard.add(telebot.types.InlineKeyboardButton(admins[admin_id]['name'], callback_data=f'admin_profile_{admin_id}'))
    admin_list_keyboard.add(telebot.types.InlineKeyboardButton("Добавить администратора➕", callback_data='add_admin'))
    admin_list_keyboard.add(telebot.types.InlineKeyboardButton("Назад", callback_data='back_to_panel'))
    return admin_list_keyboard

# Функции
def generate_token():
    return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=14))

def is_admin(user_id):
    return user_id in admins

def is_manager(user_id):
    return users.get(user_id, {}).get('role') == 'manager'

def panel(user_id, role):
    if role == 'manager':
        bot.send_message(user_id, "Панель управления", reply_markup=manager_keyboard)
    elif role == 'admin':
        bot.send_message(user_id, "Панель управления", reply_markup=admin_keyboard)
    else:
        bot.send_message(user_id, "Панель управления", reply_markup=user_keyboard)

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

# Обработчики

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    name = message.from_user.first_name
    if user_id not in users:
        users[user_id] = {'role': 'user', 'blocked_until': 0, 'admin_since': None, 'username': username, 'name': name}
    else:
        users[user_id]['username'] = username
        users[user_id]['name'] = name

    if users[user_id]['blocked_until'] > time.time():
        bot.reply_to(message, "Вы заблокированы.")
        return

    bot.reply_to(message, "Отправьте Ваше сообщение или любой другой вид информации")

    # Дополнительная логика для ролей
    if is_manager(user_id) or is_admin(user_id):
        panel(user_id, users[user_id]['role'])

@bot.message_handler(commands=['menu'])
def menu(message):
    user_id = message.from_user.id
    if is_manager(user_id):
        panel(user_id, 'manager')
    elif is_admin(user_id):
        panel(user_id, 'admin')
    else:
        bot.send_message(user_id, "Команда доступна только администраторам и распорядителям.")


@bot.message_handler(commands=['manager_aut'])
def manager_auth(message):
    user_id = message.from_user.id

    # Проверяем, авторизован ли пользователь
    if users[user_id].get('role') in ['manager', 'admin']:
        bot.reply_to(message, "Вы уже авторизованы.")
        return

    bot.send_message(user_id, "Send token")
    bot.register_next_step_handler(message, process_manager_token)

def process_manager_token(message):
    user_id = message.from_user.id
    token = message.text
    if token == manager_token:
        users[user_id] = {'role': 'manager', 'blocked_until': 0, 'admin_since': time.time()}
        bot.reply_to(message, "The manager has successfully entered")
        panel(user_id, users[user_id]['role'])
    else:
        users[user_id]['blocked_until'] = time.time() + 240 * 3600
        bot.reply_to(message, "Неверный токен. Вы заблокированы на 240 часов.")

@bot.message_handler(commands=['admin_token'])
def admin_auth(message):
    user_id = message.from_user.id

    # Проверяем, авторизован ли пользователь
    if users[user_id].get('role') in ['manager', 'admin']:
        bot.reply_to(message, "Вы уже авторизованы.")
        return

    bot.send_message(user_id, "Send token")
    bot.register_next_step_handler(message, process_admin_token)

def process_admin_token(message):
    user_id = message.from_user.id
    token = message.text
    if token in admin_tokens and admin_tokens[token] == user_id:
        users[user_id] = {'role': 'admin', 'blocked_until': 0, 'admin_since': time.time()}
        admins[user_id] = {'name': users[user_id]['name'], 'link': f"tg://user?id={user_id}", 'since': time.time()}
        admin_tokens.pop(token)
        bot.reply_to(message, "The admin has successfully entered")
        panel(user_id, users[user_id]['role'])
    else:
        users[user_id]['blocked_until'] = time.time() + 240 * 3600
        bot.reply_to(message, "Неверный или истекший токен. Вы заблокированы на 240 часов.")

@bot.message_handler(commands=['leave_rank'])
def leave_rank(message):
    user_id = message.from_user.id

    if users[user_id]['role'] in ['manager', 'admin']:
        # Откатываем чат
        clear_chat(message.chat.id)

        # Удаляем роль и admin_since
        users[user_id]['role'] = 'user'
        users[user_id]['admin_since'] = None

        # Блокируем возможность использовать команды /admin_token и /manager_token на 240 часов
        users[user_id]['blocked_until'] = time.time() + 240 * 3600

        bot.send_message(user_id, "Вы успешно покинули должность. Команды администратора/распорядителя будут недоступны в течение 240 часов.")
        start(message)  # Возвращаем к обычному состоянию пользователя
    else:
        bot.reply_to(message, "Вы не являетесь администратором или распорядителем.")

@bot.message_handler(commands=['block'])
def block_user(message):
    # /block_[id пользователя]_[кол-во часов в блокировке]
    try:
        _, user_id_to_block, duration = message.text.split('_')
        user_id_to_block = int(user_id_to_block)
        duration = int(duration)
    except ValueError:
        bot.reply_to(message, "Неверный формат команды. Используйте /block_[id пользователя]_[кол-во часов в блокировке]")
        return

    if is_manager(message.from_user.id) or (is_admin(message.from_user.id) and message.from_user.id != user_id_to_block):
        if user_id_to_block in users:
            users[user_id_to_block]['blocked_until'] = time.time() + duration * 3600
            user_name = users[user_id_to_block]['name']
            user_link = f"tg://user?id={user_id_to_block}"
            bot.reply_to(message, f"Пользователь <a href=\"{user_link}\">{user_name}</a> заблокирован✅", parse_mode='HTML')
        else:
            bot.reply_to(message, "Пользователь не найден.")
    else:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")

@bot.message_handler(commands=['unblock'])
def unblock_user(message):
    # /unblock_[id пользователя]
    try:
        _, user_id_to_unblock = message.text.split('_')
        user_id_to_unblock = int(user_id_to_unblock)
    except ValueError:
        bot.reply_to(message, "Неверный формат команды. Используйте /unblock_[id пользователя]")
        return

    if is_manager(message.from_user.id) or (is_admin(message.from_user.id) and message.from_user.id != user_id_to_unblock):
        if user_id_to_unblock in users:
            users[user_id_to_unblock]['blocked_until'] = 0
            user_name = users[user_id_to_unblock]['name']
            user_link = f"tg://user?id={user_id_to_unblock}"
            bot.reply_to(message, f"Пользователь <a href=\"{user_link}\">{user_name}</a> разблокирован✅", parse_mode='HTML')
        else:
            bot.reply_to(message, "Пользователь не найден.")
    else:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")

@bot.message_handler(commands=['def_on'])
def def_on(message):
    user_id = message.from_user.id
    if users[user_id]['role'] in ['manager', 'admin']:
        clear_chat(message.chat.id)
        users[user_id]['role'] = 'user'
        users[user_id]['admin_since'] = None
        bot.send_message(user_id, "Режим обычного пользователя активирован.")
        start(message)
    else:
        bot.reply_to(message, "Вы не являетесь администратором или распорядителем.")

@bot.message_handler(commands=['def_off'])
def def_off(message):
    user_id = message.from_user.id
    if users[user_id]['role'] == 'user':
        clear_chat(message.chat.id)
        users[user_id]['role'] = 'admin' if is_admin(user_id) else 'manager'
        bot.send_message(user_id, "Режим администратора/распорядителя активирован.")
        panel(user_id, users[user_id]['role'])
    else:
        bot.reply_to(message, "Вы должны быть в режиме обычного пользователя для выполнения этой команды.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    user_id = message.from_user.id
    username = message.from_user.username
    name = message.from_user.first_name

    if users[user_id]['blocked_until'] > time.time():
        bot.reply_to(message, "Вы заблокированы.")
        return

    # Проверяем, является ли отправитель администратором или менеджером
    if is_admin(user_id) or is_manager(user_id):
        # Отправляем сообщение всем, кроме отправителя
        for user, data in users.items():
            if user != user_id:
                # Если получатель тоже администратор или менеджер, показываем имя отправителя
                if is_admin(user) or is_manager(user):
                    bot.send_message(user, f"*Сообщение от {name}:*\n{message.text}", parse_mode="Markdown")
                else:
                    # Если получатель обычный пользователь, пишем "Неизвестен"
                    bot.send_message(user, f"*Неизвестен:*\n{message.text}", parse_mode="Markdown")
    else:
        # Если отправитель обычный пользователь, пересылаем сообщение администраторам и менеджерам для модерации
        for admin_id in admins:
            if is_admin(admin_id):
                if admin_id not in moderation_queue:
                     moderation_queue[admin_id] = []
                bot.send_message(admin_id, f"сообщение: {name} (<a href=\"tg://user?id={user_id}\">{message.from_user.first_name}</a>, ID: {user_id})", parse_mode='HTML')
                bot.send_message(admin_id, f"{message.text}", reply_markup = moderation_stop_keyboard)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == 'stop_moderation':
        panel(call.from_user.id, users[call.from_user.id]['role'])
    elif call.data == 'add_admin':
        # Логика для добавления администратора
        token = generate_token()
        admin_tokens[token] = call.from_user.id  # Сохраняем токен и ID пользователя
        bot.send_message(call.from_user.id, f"Токен для активации прав администратора: {token}")
        panel(call.from_user.id, users[call.from_user.id]['role'])
    elif call.data.startswith('admin_profile_'):
        admin_id = int(call.data.split('_')[2])
        admin = admins[admin_id]
        admin_info = f"Это 🪪<a href=\"{admin['link']}\">{admin['name']}</a>\n" \
                     f"ID: {admin_id}\n" \
                     f"Работает с ⏱️{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(admin['since']))}"

        remove_admin_keyboard = telebot.types.InlineKeyboardMarkup()
        remove_admin_keyboard.add(telebot.types.InlineKeyboardButton("Снять с должности♿️", callback_data=f'remove_admin_{admin_id}'))
        remove_admin_keyboard.add(telebot.types.InlineKeyboardButton("Назад", callback_data='back_to_admin_list'))

        bot.send_message(call.message.chat.id, admin_info, reply_markup=remove_admin_keyboard, parse_mode='HTML')
    elif call.data.startswith('remove_admin_'):
        admin_id_to_remove = int(call.data.split('_')[2])
        if is_manager(call.from_user.id):
            # Удаляем администратора
            del admins[admin_id_to_remove]
            users[admin_id_to_remove]['role'] = 'user'
            users[admin_id_to_remove]['admin_since'] = None

            # Отправляем уведомление администратору, которого удалили
            bot.send_message(admin_id_to_remove, "Вы были сняты с должности администратора.")

            bot.send_message(call.message.chat.id, "Администратор успешно снят с должности.", reply_markup=manager_keyboard)

            # Возвращаемся к панели управления
            panel(call.from_user.id, users[call.from_user.id]['role'])
        else:
            bot.answer_callback_query(call.id, "У вас нет прав для выполнения этого действия.")
    elif call.data == 'back_to_admin_list':
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=generate_admin_list_keyboard())
    elif call.data == 'back_to_panel':
        panel(call.from_user.id, users[call.from_user.id]['role'])
    elif call.data == 'Администрация🧑‍💻':
        bot.send_message(call.message.chat.id, "Список администраторов:", reply_markup=generate_admin_list_keyboard())

if __name__ == "__main__":
    bot.infinity_polling()

