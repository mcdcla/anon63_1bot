import telebot
import time
from datetime import datetime, timezone
from telebot import types

# --- Токен Бота ---
BOT_TOKEN = "7413834924:AAEqqeIU8XnkYzCIW1noJrhr_fKFzbTFoZI"  # Замените на токен вашего бота
bot = telebot.TeleBot("7413834924:AAEqqeIU8XnkYzCIW1noJrhr_fKFzbTFoZI")

# --- Токен Супер-Менеджера и Переменная Супер-Менеджера ---
super_manager_token = "3d806cz78"
manager = None  # ID пользователя, который является супер-менеджером

# ---  Словари для хранения данных пользователей и админов ---
users = {}  # {user_id: {'role': 'user'/'admin'/'manager', 'blocked_until': timestamp, 'username': username, 'name': first_name, 'admin_since': timestamp}}
admins = {} # {user_id: {'added_by': user_id менеджера или админа, 'since': timestamp}}

# --- Состояние модерации  ---
is_moderating = {} # {chat_id: True/False}, указывает, модерирует ли админ сейчас сообщения

# --- Блокировка от повторного /leave_rank ---
leave_rank_cooldown = {} # {user_id: timestamp}, когда пользователь сможет снова использовать команду /leave_rank

# --- Функции для проверки прав ---
def is_manager(user_id):
    return users.get(user_id, {}).get('role') == 'manager'

def is_admin(user_id):
    return users.get(user_id, {}).get('role') == 'admin'

# --- Клавиатуры ---
def create_main_keyboard():
    keyboard = types.ReplyKeyboardRemove()
    return keyboard

def create_admin_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    moderate_button = types.InlineKeyboardButton(text="Модерация сообщений📰", callback_data="start_moderate")
    send_message_button = types.InlineKeyboardButton(text="Написать сообщение✍️", callback_data="send_message")
    admin_management_button = types.InlineKeyboardButton(text="Администрация🧑‍💻", callback_data="admin_management")
    keyboard.add(moderate_button)
    keyboard.add(send_message_button)
    keyboard.add(admin_management_button)
    return keyboard

def create_stop_moderation_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    stop_moderate_button = types.InlineKeyboardButton(text="Остановить модерацию⛔️", callback_data="stop_moderation")
    keyboard.add(stop_moderate_button)
    return keyboard

def create_admin_list_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    for admin_id, admin_data in admins.items():
        if admin_id in users:
            username = users[admin_id]['username']
            first_name = users[admin_id]['name']
            admin_user_link = f"tg://user?id={admin_id}"
            button_text = f"{first_name}"
            admin_button = types.InlineKeyboardButton(text=button_text, callback_data=f"admin_profile_{admin_id}")
            keyboard.add(admin_button)
    add_admin_button = types.InlineKeyboardButton(text="добавить администратора➕", callback_data="add_admin")
    back_button = types.InlineKeyboardButton(text = "Назад", callback_data="back_to_panel")
    keyboard.add(add_admin_button)
    keyboard.add(back_button)
    return keyboard

def create_admin_profile_keyboard(admin_id):
    keyboard = types.InlineKeyboardMarkup()
    username = users[admin_id]['username']
    first_name = users[admin_id]['name']
    admin_user_link = f"tg://user?id={admin_id}"
    remove_admin_button = types.InlineKeyboardButton(text="Снять с должности♿️", callback_data=f"remove_admin_{admin_id}")
    keyboard.add(remove_admin_button)
    return keyboard

# --- Функции отправки сообщений ---
def send_moderation_message(user_id, message, admin_id):
    """Пересылает сообщение от пользователя администратору/менеджеру."""
    # Getting user info
    user_data_link = f"tg://user?id={user_id}"  # Create link to user's profile

    if is_moderating.get(admin_id, False):
        try:
            if message.text:
                bot.send_message(admin_id, f"[{first_name}](tg://user?id={user_id}), {user_id}\n{message.text}", parse_mode="Markdown")
            elif message.photo:
                file_id = message.photo[-1].file_id
                file_info = bot.get_file(file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                bot.send_photo(admin_id, downloaded_file, caption=f"Фотография от [{first_name}](tg://user?id={user_id}), {user_id}", parse_mode="Markdown")
            elif message.video:
                file_id = message.video.file_id
                file_info = bot.get_file(file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                bot.send_video(admin_id, downloaded_file, caption=f"Видео от [{first_name}](tg://user?id={user_id}), {user_id}", parse_mode="Markdown")

            elif message.audio:
                file_id = message.audio.file_id
                file_info = bot.get_file(file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                bot.send_audio(admin_id, downloaded_file, caption=f"Аудио от [{first_name}](tg://user?id={user_id}), {user_id}", parse_mode="Markdown")
            elif message.document:
                file_id = message.document.file_id
                file_info = bot.get_file(file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                bot.send_document(admin_id, downloaded_file, caption=f"Документ от [{first_name}](tg://user?id={user_id}), {user_id}", parse_mode="Markdown")

            elif message.sticker:
                 bot.send_sticker(admin_id, message.sticker.file_id, caption=f"Стикер от [{first_name}](tg://user?id={user_id}), {user_id}", parse_mode="Markdown")
            elif message.location:
                bot.send_location(admin_id, message.location.latitude, message.location.longitude, caption=f"Локация от [{first_name}](tg://user?id={user_id}), {user_id}", parse_mode="Markdown")

            elif message.contact:
                caption = f"Контакт от [{first_name}](tg://user?id={user_id}), {user_id}"
                bot.send_contact(admin_id, message.contact.phone_number, message.contact.first_name, caption=caption, parse_mode="Markdown")

            elif message.voice:
                file_id = message.voice.file_id
                file_info = bot.get_file(file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                bot.send_voice(admin_id, downloaded_file, caption=f"Голосовое сообщение от [{first_name}](tg://user?id={user_id}), {user_id}", parse_mode="Markdown")

            else:
                bot.send_message(admin_id, f"Неизвестный тип сообщения от [{first_name}](tg://user?id={user_id}), {user_id}", parse_mode="Markdown")
        except Exception as e:
            print(f"Ошибка при пересылке сообщения администратору {admin_id}: {e}")

def send_message_to_admins_managers(user_id, message):
    """Отправляет сообщение от админа/менеджера другим админам и менеджерам."""
    username = users[user_id]['username']
    first_name = users[user_id]['name']
    for u_id, u_data in users.items():
        if (is_admin(u_id) or is_manager(u_id)) and u_id != user_id:
           try:
                sender = "Неизвестен"
                if is_manager(user_id):
                    sender = f"[{first_name}](tg://user?id={user_id})"
                if message.text:
                    bot.send_message(u_id, f"Сообщение от {sender}:\n{message.text}", parse_mode="Markdown")
                elif message.photo:
                    file_id = message.photo[-1].file_id
                    file_info = bot.get_file(file_id)
                    downloaded_file = bot.download_file(file_info.file_path)
                    bot.send_photo(u_id, downloaded_file, caption=f"Фотография от {sender}", parse_mode="Markdown")
                elif message.video:
                    file_id = message.video.file_id
                    file_info = bot.get_file(file_id)
                    downloaded_file = bot.download_file(file_info.file_path)
                    bot.send_video(u_id, downloaded_file, caption=f"Видео от {sender}", parse_mode="Markdown")
                elif message.sticker:
                    bot.send_sticker(u_id, message.sticker.file_id, caption=f"Стикер от {sender}", parse_mode="Markdown")

                else:
                    bot.send_message(u_id, f"Сообщение от {sender}", parse_mode="Markdown")
           except Exception as e:
                print(f"Ошибка при пересылке сообщения пользователю {u_id}: {e}")

def send_panel(user_id):
    """Отправляет панель управления в зависимости от роли пользователя."""
    if is_manager(user_id) or is_admin(user_id):
        bot.send_message(user_id, "Панель управления", reply_markup=create_admin_keyboard())
    else:
        bot.send_message(user_id, "У вас нет прав для просмотра панели управления.")

# --- Удаление сообщения ---
def delete_message(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")

def delete_all_messages(chat_id):
    try:
        # Получаем последние сообщения в чате
        messages = bot.get_chat_history(chat_id, limit=100)  # Можно увеличить лимит, если нужно

        # Удаляем сообщения
        for message in messages:
            delete_message(chat_id, message.message_id)

        bot.send_message(chat_id, "Чат очищен.")
    except Exception as e:
        print(f"Ошибка при удалении всех сообщений: {e}")

# --- Обработчики команд ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    if user_id not in users:
        users[user_id] = {'role': 'user', 'blocked_until': 0, 'username': username, 'name': first_name, 'admin_since': None}
    else:
        #Если это админ/менеджер, отправляем панель
        if is_admin(user_id) or is_manager(user_id):
            send_panel(user_id)
            return

    bot.reply_to(message, "Отправьте Ваше сообщение или любой другой вид информации", reply_markup=create_main_keyboard())

# --- Обработчик команды "manager_aut" ---
@bot.message_handler(commands=['manager_aut'])
def manager_aut_handler(message):
    """Запрашивает токен для назначения супер-менеджера."""
    user_id = message.from_user.id

    if is_admin(user_id) or is_manager(user_id):
        bot.reply_to(message, "Вы уже авторизованы")
        return
    bot.reply_to(message, "send token")
    bot.register_next_step_handler(message, process_manager_token)

def process_manager_token(message):
    """Проверяет токен и назначает супер-менеджера."""
    global manager
    token = message.text
    user_id = message.from_user.id
    if token == super_manager_token:
        users[user_id]['role'] = 'manager'
        manager = user_id
        bot.reply_to(message, "The manager has successfully entered")
        send_panel(user_id)  # Отобразить панель управления
    else:
         users[user_id]['blocked_until'] = time.time() + 240 * 3600
         bot.reply_to(message, "Неверный токен. Вы заблокированы на 240 часов.")

@bot.message_handler(commands=['admin_activate'])
def admin_activate_handler(message):
    """Активация прав администратора."""
    user_id = message.from_user.id

    if is_admin(user_id) or is_manager(user_id):
        bot.reply_to(message, "Вы уже авторизованы")
        return

    if user_id in admins:
        users[user_id]['role'] = 'admin'
        users[user_id]['admin_since'] = time.time()
        bot.reply_to(message, "You activate administrator perms")
        send_panel(user_id)
    else:
        users[user_id]['blocked_until'] = time.time() + 240 * 3600
        bot.reply_to(message, "Вы не активированны. Установлена блокировка на 240 часов")

@bot.message_handler(commands=['block'])
def block_user_handler(message):
    """Блокирует пользователя (только для администраторов и менеджеров)."""
    user_id = message.from_user.id

    if not (is_manager(user_id) or is_admin(user_id)):
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return

    try:
        parts = message.text.split('_')
        user_id_to_block = int(parts[1])
        block_hours = int(parts[2])
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
    bot.reply_to(message, f"пользователь [{first_name}](tg://user?id={user_id_to_block}) заблокирован✅", parse_mode="Markdown")

@bot.message_handler(commands=['unblock'])
def unblock_user_handler(message):
    """Разблокирует пользователя (только для администратора)."""
    user_id = message.from_user.id

    if not (is_manager(user_id) or is_admin(user_id)):
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

    users[user_id_to_unblock]['blocked_until'] = 0
    username = users[user_id_to_unblock]['username']
    first_name = users[user_id_to_unblock]['name']
    user_link = f"tg://user?id={user_id_to_unblock}"
    bot.reply_to(message, f"пользователь [{first_name}](tg://user?id={user_id_to_unblock}) разблокирован✅", parse_mode="Markdown")

@bot.message_handler(commands=['def_on'])
def default_on_handler(message):
    """Установка роли пользователя по умолчанию (только для администратора)."""
    user_id = message.from_user.id
    if not (is_manager(user_id) or is_admin(user_id)):
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return

    users[user_id]['role'] = 'user'
    delete_all_messages(message.chat.id)
    start(message)

@bot.message_handler(commands=['def_off'])
def default_off_handler(message):
    """Возврат к режиму администратора (только для администратора)."""
    user_id = message.from_user.id
    if not (is_manager(user_id) or is_admin(user_id)):
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return
    delete_all_messages(message.chat.id)
    users[user_id]['role'] = 'admin'
    send_panel(user_id)

@bot.message_handler(commands=['leave_rank'])
def leave_rank_handler(message):
    """Пользователь самостоятельно уходит с поста"""
    user_id = message.from_user.id
    if not (is_manager(user_id) or is_admin(user_id)):
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return
    if user_id in leave_rank_cooldown and leave_rank_cooldown[user_id] > time.time():
        remaining_time = time.strftime("%H:%M:%S", time.gmtime(leave_rank_cooldown[user_id] - time.time())) # Format the remaining time
        bot.reply_to(message, f"Вы сможете воспользоваться данной командой только через {remaining_time}")
        return
    # Set the 240 hour cooldown
    leave_rank_cooldown[user_id] = time.time() + 240 * 3600
    delete_all_messages(message.chat.id)
    users[user_id]['role'] = 'user'
    users[user_id]['admin_since'] = None
    admins.pop(user_id, None)
    bot.send_message(user_id, "Вы покинули должность. Отправьте /start") #Добавлено напоминание
    #start(message)

@bot.message_handler(commands=['menu'])
def menu_handler(message):
    """Панель управления"""
    user_id = message.from_user.id
    if not (is_manager(user_id) or is_admin(user_id)):
        return
    send_panel(user_id)

@bot.message_handler(commands=['admin_add'])
def admin_add_handler(message):
    """Добавление администратора без токена (только для менеджера)."""
    user_id = message.from_user.id

    if not is_manager(user_id):
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return

    try:
        user_id_to_add = int(message.text.split('_')[1])
    except (IndexError, ValueError):
        bot.reply_to(message, "Неверный формат команды. Используйте: /admin_add_[ID пользователя]")
        return

    if user_id_to_add not in users:
        bot.reply_to(message, "Пользователь с таким ID не найден.")
        return

    admins[user_id_to_add] = {'added_by': user_id, 'since': time.time()}
    bot.reply_to(message, "Администратор добавлен✅ Администратор начнёт работу после прописания команды /admin_activate")

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
        bot.reply_to(message, "Ваше сообщение доставлено")
        send_message_to_admins_managers(user_id, message)

# --- Callback Query Handlers ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if call.data == 'start_moderate':
        # Логика начала модерации сообщений
        if is_admin(user_id) or is_manager(user_id):
            if not is_moderating.get(chat_id, False):
                is_moderating[chat_id] = True
                bot.send_message(user_id, "Вам поступают сообщения от обычных пользователей", reply_markup=create_stop_moderation_keyboard())
            else:
                bot.send_message(user_id, "Вы уже модерируете сообщения.")
        else:
            bot.answer_callback_query(call.id, "У вас нет прав для модерации.")

    elif call.data == 'stop_moderation':
        # Логика остановки модерации сообщений
        if is_admin(user_id) or is_manager(user_id):
            if is_moderating.get(chat_id, False):
                is_moderating[chat_id] = False
                bot.send_message(user_id, "панель управления", reply_markup=create_admin_keyboard())
            else:
                bot.send_message(user_id, "Вы не модерируете сообщения в данный момент.")
        else:
            bot.answer_callback_query(call.id, "У вас нет прав для остановки модерации.")

    elif call.data == 'send_message':
        bot.send_message(user_id, "введите Ваше сообщение")
        bot.register_next_step_handler(call.message, process_admin_message)

    elif call.data == 'admin_management':
        bot.edit_message_text("администраторы", user_id, message_id, reply_markup=create_admin_list_keyboard())

    elif call.data.startswith('admin_profile_'):
        admin_id = int(call.data[len('admin_profile_'):])
        admin_info = admins[admin_id]
        # Format the admin info
        username = users[admin_id]['username']
        first_name = users[admin_id]['name']
        admin_user_link = f"tg://user?id={admin_id}"
        admin_since = users[admin_id].get('admin_since')

        if admin_since:
            since_date = datetime.fromtimestamp(admin_since, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        else:
            since_date = "Администратор не активирован😟"

        message_text = (
            f"Это 🪪[{first_name}](tg://user?id={admin_id})\n"
            f"ID: {admin_id}\n"
            f"Работает с ⏱️{since_date}"
        )

        bot.edit_message_text(message_text, user_id, message_id, reply_markup=create_admin_profile_keyboard(admin_id), parse_mode="Markdown")

    elif call.data == 'add_admin':
        #Менеджер добавляет другого админа
        bot.send_message(user_id, "Введите ID или юзернейм пользователя")
        bot.register_next_step_handler(call.message, process_add_admin)
        return

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
        bot.delete_message(chat_id, message_id)
        delete_all_messages(admin_id_to_remove)

        bot.answer_callback_query(call.id, f"Администратор [{first_name}](tg://user?id={admin_id_to_remove}) был снят с должности.", parse_mode="Markdown")
        bot.edit_message_text("администраторы", user_id, message_id, reply_markup=create_admin_list_keyboard())
    else:
        bot.answer_callback_query(call.id, "Действие не поддерживается.")

def process_add_admin(message):
    """Обрабатывает ID или юзернейм нового администратора."""
    user_id = message.from_user.id
    try:
        if message.text.startswith('@'):
            #Поиск пользователя по юзернейму
            new_admin_username = message.text[1:]
            try:
               new_admin = bot.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id) # Исправлено: Получаем информацию о пользователе по user_id

               new_admin_id = new_admin.user.id
            except Exception as e:
                bot.reply_to(message, f"Пользователь с таким юзернеймом не найден.")
                send_panel(user_id)
                return
        else:
            new_admin_id = int(message.text)
        if new_admin_id not in users:
            bot.reply_to(message, "Пользователь с таким ID не найден.")
            send_panel(user_id)
            return

        admins[new_admin_id] = {'added_by': user_id, 'since': time.time()}
        bot.reply_to(message, "Администратор добавлен✅ Администратор начнёт работу после прописания команды /admin_activate")
    except ValueError:
        bot.reply_to(message, "Неверный формат ID или юзернейма.")
    send_panel(user_id)

def process_admin_message(message):
    """Обрабатывает сообщение, отправленное администратором/менеджером."""
    user_id = message.from_user.id
    bot.reply_to(message, "Ваше сообщение доставлено")
    # Отправляем сообщение всем админам и менеджерам, кроме отправителя
    send_message_to_admins_managers(user_id, message)
    send_panel(user_id)

# --- Запуск бота ---
if __name__ == '__main__':
    bot.infinity_polling()
