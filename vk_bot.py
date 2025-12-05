import os
import sys
import logging
import random
from datetime import datetime
from threading import Thread
import time
import threading

# Устанавливаем кодировку
sys.stdout.reconfigure(encoding='utf-8')

# Пытаемся загрузить dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env файл загружен")
except ImportError:
    print("⚠️  python-dotenv не установлен")
except Exception as e:
    print(f"⚠️  Ошибка загрузки .env: {e}")

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

# ========== НАСТРОЙКИ ==========
# Загрузка переменных окружения
VK_TOKEN = os.getenv('VK_TOKEN')
GROUP_ID = os.getenv('GROUP_ID')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

COMPANY_INFO = {
    'experience': '4 года',
    'completed_projects': '1000',
    'production_time': '21 день',
    'warranty': '2',
    'kitchen_price_from': '100 000',
    'wardrobe_price_from': '70 000',
    'website': 'sohokitchen.ru',
    'telegram': 't.me/soho_kitchen',
    'phone': ('\n'
             '+7 (499) 110-71-89\n'
             '+7 (977) 984-66-96\n'
             '+7 (925) 459-64-39'
    ),
    'email': 'Soho.kitchen@yandex.ru',
    'address': 'г. Москва, ул. Нарвская, д. 23',
    'work_hours': ('\n'
        '• пн-пт 10:00-19:00 (офис)\n'
        '• пн-пт 9:00-20:00 (дизайнер)'
    )
}

# ========== НАСТРОЙКИ ФОТОГРАФИЙ ==========
# ВАЖНО: Замените эти ID на реальные ID фотографий из вашего сообщества VK
# Формат: photo-{owner_id}_{photo_id}
WELCOME_PHOTOS = [
    'photo-234418631_456239017',  # Замените на реальные ID
    'photo-234418631_456239021',
    'photo-234418631_456239020',
    'photo-234418631_456239019',
    'photo-234418631_456239018',
    'photo-234418631_456239017',
]

# ========== НАСТРОЙКА ЛОГГИРОВАНИЯ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальный словарь для хранения данных пользователей
user_data = {}

# ========== НАСТРОЙКИ НАПОМИНАНИЙ ==========
REMINDER_ENABLED = False  # Включить/выключить напоминания
REMINDER_CHECK_INTERVAL = 3600  # Проверка каждые 60 минут (в секундах)
REMINDER_INTERVAL_1 = 6 * 3600  # Первое напоминание через 6 часов (в секундах)
REMINDER_INTERVAL_2 = 24 * 3600  # Второе напоминание через 24 часа (в секундах)

# Тексты напоминаний
REMINDER_1_TEXT = """⏰ Напоминание от кухонной фабрики Soho!

Вы начинали диалог с нашим ботом, но не завершили заявку.

🎁 Не забудьте про наши преимущества:
• Бесплатный 3D дизайн-проект
• Скидка 30% при быстром решении
• Подарок - встроенная техника
• Рассрочка 0% на 24 месяца

Просто продолжите диалог с ботом для получения точного расчета! 😊"""

REMINDER_2_TEXT = """🍽️ Последнее напоминание от Soho!

Вы интересовались нашей мебелью, но не завершили заявку.

⚠️ Специальные условия действуют ограниченное время!

Успейте получить:
✅ Максимальную скидку 30%
✅ Бесплатный дизайн-проект
✅ Технику в подарок (вытяжка, мойка или плита)
✅ Рассрочку без переплат

👉 Просто ответьте на это сообщение или воспользуйтесь ботом

P.S. Это последнее напоминание. Больше не будем беспокоить.

С уважением, команда Soho Kitchen!"""

# Указатель на каком напоминании какой текст использовать
REMINDER_TEXTS = {
    1: REMINDER_1_TEXT,
    2: REMINDER_2_TEXT
}
# ========== КЛАВИАТУРЫ VK ==========

def get_main_keyboard():
    """Основная клавиатура"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("📞 Заказать звонок", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("💰 Рассчитать стоимость", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("📍 Контакты", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("👷 Вызвать замерщика", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("📸 Примеры работ", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

def get_back_keyboard():
    """Клавиатура только с кнопкой Назад"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("◀️ Назад в меню", color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()

def get_phone_keyboard():
    """Клавиатура для запроса телефона"""
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("◀️ Назад в меню", color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()

def get_calculate_keyboard():
    """Клавиатура для выбора типа расчета"""
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("🎨 Кухня", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("🚪 Шкаф", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("◀️ Назад в меню", color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()

def get_kitchen_type_keyboard():
    """Тип кухни"""
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Прямая", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("Угловая", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("П-образная", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("Островная", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("◀️ Отмена", color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()

def get_wardrobe_type_keyboard():
    """Тип шкафа"""
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Купе", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("Угловой", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("Распашной", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("Гардеробная", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("Другой вариант", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("◀️ Отмена", color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()

def get_size_keyboard():
    """Клавиатура для выбора типа ввода размеров"""
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("📏 Я знаю точный размер", color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button("❓ Знаю только приблизительно", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("❔ Еще не знаю размер", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("◀️ Назад", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_button("◀️ Отмена", color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()

def get_design_project_keyboard():
    """Дизайн-проект"""
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Да", color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button("Нет", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_button("Нужен проект", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("◀️ Отмена", color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()

def get_timeframe_keyboard():
    """Сроки покупки"""
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("В ближайшее время", color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button("В течение месяца", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("В течение 2-х месяцев", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("◀️ Отмена", color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()

def get_deadline_keyboard():
    """Сроки с подарками"""
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("В ближайшее время (Скидка 30% и подарок)", color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button("В течение месяца (Скидка 15% и подарок)", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("В течение 2-х месяцев", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("◀️ Отмена", color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()

def get_phone_final_keyboard():
    """Финальная клавиатура"""
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("◀️ Назад", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("◀️ Отмена", color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()

# ========== ТЕКСТЫ СООБЩЕНИЙ ==========

def get_welcome_message(user_name):
    """Приветственное сообщение"""
    return f"""🍽️ Вас приветствует кухонная фабрика Soho!

Здравствуйте, {user_name}!

✅ Для расчета цены, жмите кнопку ниже! 👇

За {COMPANY_INFO['experience']} работы мы сделали мебель для более, чем {COMPANY_INFO['completed_projects']} семей из Москвы и области!
Мы прямой производитель кухонь и шкафов в Москве и области, поэтому вы не переплачиваете посредникам и с нами сэкономите минимум 30-40%

🔸 Собственное производство в Подмосковье;
🔸 Изготовление мебели на высокоточном оборудовании;
🔸 Средний срок от замера до сборки {COMPANY_INFO['production_time']};
🔸 Гарантия на мебель {COMPANY_INFO['warranty']} года;
🔸 3D дизайн-проект мебели бесплатный;
🔸 Рассрочка без первоначального взноса и переплат;
🔸 Индивидуальные скидки и подарки при заказе.

✅ Делаем мебель по вашим пожеланиям и с учетом особенностей помещения. Используем каждый миллиметр полезной площади для вашего удобства.

✅ Используем в производстве только качественные и экологичные материалы. Поэтому наша мебель служит десятилетиями.

✅ Контроль качества на каждом этапе от бесплатного дизайн-проекта до установки готового изделия.

✅ Цены на наши кухни начинаются от {COMPANY_INFO['kitchen_price_from']}₽, используем мы только качественные фасады и фурнитуру, корпуса ЛДСП EGGER (класс эмиссии Е0.5) и МДФ (с различными типами покрытий), что обеспечивает их долговечность и функциональность.

✅ Цены на наши шкафы начинаются от {COMPANY_INFO['wardrobe_price_from']}₽

✅ Мы уверены в своих материалах, именно поэтому гарантия на наши кухни {COMPANY_INFO['warranty']} года

✅ Более {COMPANY_INFO['completed_projects']} кухонь и шкафов мы уже изготовили в Москве и области

✅ Есть рассрочка без % от 6 до 24-х месяцев

🎁 Рассчитайте стоимость вашей мебели за 1 минуту и при заказе получите встроенную технику в подарок на выбор: вытяжка, мойка или плита!

Для расчета цены, жмите кнопку ниже! 👇"""

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def get_user_name(vk, user_id):
    """Получение имени пользователя"""
    try:
        user_info = vk.users.get(user_ids=user_id)[0]
        return user_info.get('first_name', 'клиент')
    except:
        return 'клиент'

def send_message(vk, user_id, message, keyboard=None):
    """Отправка сообщения пользователю"""
    try:
        import random
        import time
        
        # Комбинируем timestamp и случайное число
        timestamp = int(time.time() * 1000)  # миллисекунды
        random_part = random.randint(0, 999999)
        random_id = (timestamp << 20) | random_part
        
        vk.messages.send(
            user_id=user_id,
            message=message,
            keyboard=keyboard,
            random_id=random_id
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        return False

def send_message_with_photos(vk, user_id, message, photos=None, keyboard=None):
    """Отправка сообщения с фотографиями"""
    try:
        import random
        import time
        
        timestamp = int(time.time() * 1000)
        random_part = random.randint(0, 999999)
        random_id = (timestamp << 20) | random_part
        
        if photos and isinstance(photos, list) and len(photos) > 0:
            # Формируем attachment строку с фотографиями
            # VK позволяет до 10 фотографий в одном сообщении
            attachments = ','.join(photos[:10])
            
            vk.messages.send(
                user_id=user_id,
                message=message,
                keyboard=keyboard,
                attachment=attachments,
                random_id=random_id
            )
        else:
            vk.messages.send(
                user_id=user_id,
                message=message,
                keyboard=keyboard,
                random_id=random_id
            )
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения с фото: {e}")
        return False

def is_valid_phone_number(text: str) -> bool:
    """Проверяет, является ли текст валидным номером телефона"""
    cleaned = ''.join(filter(str.isdigit, text))
    
    if len(cleaned) < 10:
        return False
    
    if cleaned.startswith(('7', '8', '9')):
        if cleaned.startswith(('7', '8')) and len(cleaned) >= 2 and cleaned[1] == '9':
            return True
        elif cleaned.startswith('9'):
            return True
    
    return False

def format_phone_number(text: str) -> str:
    """Форматирует номер телефона"""
    digits = ''.join(filter(str.isdigit, text))
    
    if len(digits) == 10:
        digits = '7' + digits
    elif digits.startswith('8') and len(digits) == 11:
        digits = '7' + digits[1:]
    
    return '+' + digits

def send_reminder_to_admin(vk, message_text):
    """Отправка напоминания админу"""
    time.sleep(300)  # 60 секунд задержка
    try:
        vk.messages.send(
            user_id=ADMIN_ID,
            message=message_text,
            random_id=random.randint(0, 2**64)
        )
    except Exception as e:
        logger.error(f"Ошибка отправки напоминания: {e}")

def send_simple_request(vk, user_id, user_name, phone_number, request_type, is_manual=False):
    """Отправка простой заявки (звонок или замерщик)"""
    formatted_phone = format_phone_number(phone_number)
    phone_source = "вручную" if is_manual else "из профиля"
    
    # Сообщение админу
    admin_message = f"""📞 НОВАЯ ЗАЯВКА: {request_type}

👤 Клиент:
• Имя: {user_name}
• ID: {user_id}
• Телефон: {formatted_phone} ({phone_source})

📅 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"""
    
    # Сообщение пользователю
    user_message = f"""✅ Спасибо, {user_name}!

Ваша заявка на {request_type} принята!

📞 Наш менеджер свяжется с вами как можно скорее
👤 Ваш номер: {formatted_phone}

🎁 Не забудьте спросить про подарок!

До связи!"""
    
    try:
        # Отправляем админу
        send_message(vk, ADMIN_ID, admin_message)
        
        # Уведомляем пользователя
        send_message(vk, user_id, user_message, get_main_keyboard())
        
        logger.info(f"Заявка: {request_type} от {user_id}")
        
        # Запускаем напоминание в отдельном потоке
        reminder = f"⏰ Напоминание: {request_type} от {user_name} ({formatted_phone})"
        Thread(target=send_reminder_to_admin, args=(vk, reminder)).start()
        
        # Очищаем данные пользователя
        if user_id in user_data:
            del user_data[user_id]
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        send_message(vk, user_id, "❌ Ошибка обработки. Позвоните нам: " + COMPANY_INFO['phone'], get_main_keyboard())

def send_form_to_admin(vk, user_id, user_name, phone_number, is_manual=False):
    """Отправка заполненной формы админу"""
    if user_id not in user_data:
        return
    
    form_type = user_data[user_id].get('form_type', 'НЕИЗВЕСТНО')
    form_data = user_data[user_id].get('form_data', {})
    
    formatted_phone = format_phone_number(phone_number)
    phone_source = "вручную" if is_manual else "из профиля"
    
    # Формируем сообщение админу
    admin_message = f"""📋 НОВАЯ ЗАЯВКА НА РАСЧЕТ: {form_type}

👤 КЛИЕНТ:
• Имя: {user_name}
• ID: {user_id}
• Телефон: {formatted_phone} ({phone_source})

📝 ДАННЫЕ ИЗ ОПРОСНИКА:"""
    
    if form_type == 'КУХНЯ':
        admin_message += f"""
🍽️ ХАРАКТЕРИСТИКИ КУХНИ:
1. Конфигурация: {form_data.get('type', 'Не указано')}
2. Размеры: {form_data.get('size', 'Не указано')}
3. Сроки: {form_data.get('deadline', 'Не указано')}"""
    elif form_type == 'ШКАФ':
        admin_message += f"""
🚪 ХАРАКТЕРИСТИКИ ШКАФА:
1. Тип шкафа: {form_data.get('type', 'Не указано')}
2. Размеры: {form_data.get('size', 'Не указано')}
3. Дизайн-проект: {form_data.get('design_project', 'Не указано')}
4. Срок покупки: {form_data.get('timeframe', 'Не указано')}"""
    
    admin_message += f"""
📅 ДАТА: {datetime.now().strftime('%d.%m.%Y %H:%M')}
🏭 ИСТОЧНИК: VK бот Soho"""
    
    # Сообщение пользователю
    user_message = f"""✅ Спасибо, {user_name}!

Ваша заявка на расчет {form_type.lower()} принята!

📋 Ваши ответы:"""
    
    if form_type == 'КУХНЯ':
        user_message += f"""
• Конфигурация: {form_data.get('type', '—')}
• Размеры: {form_data.get('size', '—')}
• Сроки: {form_data.get('deadline', '—')}"""
    elif form_type == 'ШКАФ':
        user_message += f"""
• Тип: {form_data.get('type', '—')}
• Размеры: {form_data.get('size', '—')}
• Дизайн-проект: {form_data.get('design_project', '—')}
• Срок покупки: {form_data.get('timeframe', '—')}"""
    
    user_message += f"""
📞 Ваш номер: {formatted_phone}
⏰ Наш дизайнер свяжется с вами как можно скорее

🎁 Не забудьте спросить про подарок!"""
    
    try:
        # Отправляем админу
        send_message(vk, ADMIN_ID, admin_message)
        
        # Уведомляем пользователя
        send_message(vk, user_id, user_message, get_main_keyboard())
        
        logger.info(f"Новая форма: {form_type} от {user_id}, телефон: {formatted_phone}")
        
        # Запускаем напоминание в отдельном потоке
        reminder = f"⏰ Напоминание: Заявка на {form_type} от {user_name} ({formatted_phone})"
        Thread(target=send_reminder_to_admin, args=(vk, reminder)).start()
        
        # Очищаем данные пользователя
        if user_id in user_data:
            del user_data[user_id]
        
    except Exception as e:
        logger.error(f"Ошибка отправки формы: {e}")
        send_message(vk, user_id, "❌ Ошибка обработки. Позвоните нам: " + COMPANY_INFO['phone'], get_main_keyboard())

# ========== ОСНОВНАЯ ЛОГИКА ==========

def handle_message(vk, user_id, text):
    """Обработка текстовых сообщений"""
    user_name = get_user_name(vk, user_id)
    
    # Инициализируем данные пользователя если их нет
    if user_id not in user_data:
        user_data[user_id] = {
            'form_type': None,
            'form_data': {},
            'current_step': 0,
            'waiting_for_custom_type': False,
            'waiting_for_size_type': False,  # Новое поле: ожидаем тип размера
            'last_action': None,
            'last_activity': datetime.now().timestamp(),
            'reminder_sent_1': False,
            'reminder_sent_2': False,
            'reminders_disabled': False
        }
    
    # Обновляем время последней активности
    user_data[user_id]['last_activity'] = datetime.now().timestamp()
    
    # Сбрасываем напоминания если пользователь ответил
    user_data[user_id]['reminder_sent_1'] = False
    user_data[user_id]['reminder_sent_2'] = False
    
    data = user_data[user_id]
    form_type = data.get('form_type')
    current_step = data.get('current_step', 0)
    waiting_for_size_type = data.get('waiting_for_size_type', False)
    
    # ========== ОБРАБОТКА КОМАНД НАВИГАЦИИ ==========
    
    # Обработка команды "◀️ Назад в меню" для всех этапов
    if text == "◀️ Назад в меню":
        cancel_form(user_id)
        send_message(vk, user_id, "Главное меню:", get_main_keyboard())
        return
    
    # Обработка команды "◀️ Назад" (из форм)
    if text == "◀️ Назад":
        if form_type == 'КУХНЯ':
            if current_step == 2:
                # Возврат от размеров к типу кухни
                data['current_step'] = 1
                send_message(
                    vk, 
                    user_id, 
                    f"🎨 Расчет стоимости кухни\n\n"
                    f"{user_name}, ответьте на 3 вопроса для точного расчета.\n\n"
                    f"1/3. Какая конфигурация кухни вам нужна?\n\n"
                    f"Текущий выбор: {data['form_data'].get('type', 'не выбран')}",
                    get_kitchen_type_keyboard()
                )
                return
            elif current_step == 3:
                # Возврат от сроков к размерам
                data['current_step'] = 2
                send_message(
                    vk, 
                    user_id, 
                    f"2/3. Какие примерные размеры?\n\n"
                    f"Текущий ответ: {data['form_data'].get('size', 'не указан')}",
                    get_back_keyboard()
                )
                return
                
        elif form_type == 'ШКАФ':
            if current_step == 2:
                # Возврат от размеров к типу шкафа
                data['current_step'] = 1
                send_message(
                    vk, 
                    user_id, 
                    f"🚪 Расчет стоимости шкафа\n\n"
                    f"{user_name}, ответьте на 4 вопроса для точного расчета.\n\n"
                    f"1/4. Какой тип шкафа вам нужен?\n\n"
                    f"Текущий выбор: {data['form_data'].get('type', 'не выбран')}",
                    get_wardrobe_type_keyboard()
                )
                return
            elif current_step == 3:
                # Возврат от дизайн-проекта к размерам
                data['current_step'] = 2
                send_message(
                    vk, 
                    user_id, 
                    f"2/4. Какие размеры шкафа?\n\n"
                    f"Текущий ответ: {data['form_data'].get('size', 'не указан')}",
                    get_back_keyboard()
                )
                return
            elif current_step == 4:
                # Возврат от сроков к дизайн-проекту
                data['current_step'] = 3
                send_message(
                    vk, 
                    user_id, 
                    f"3/4. Есть ли у вас дизайн-проект?\n\n"
                    f"Текущий ответ: {data['form_data'].get('design_project', 'не выбран')}",
                    get_design_project_keyboard()
                )
                return
        return
    
    # ========== ОБРАБОТКА ОПРОСНИКА ==========
    
    # КУХНЯ (3 вопроса + телефон)
    if form_type == 'КУХНЯ' and 1 <= current_step <= 3:
        if text == "◀️ Отмена":
            cancel_form(user_id)
            send_message(vk, user_id, "❌ Заполнение формы отменено.", get_main_keyboard())
            return
            
        if current_step == 1:
            # Тип кухни
            data['form_data']['type'] = text
            data['current_step'] = 2
            
            send_message(
                vk, 
                user_id, 
                f"✅ Конфигурация: {text}\n\n"
                f"2/3. Какие размеры кухни?\n\n"
                f"Вы можете:\n"
                f"• 📏 Указать точные размеры (например: 3х2.5м)\n"
                f"• ❓ Указать приблизительные размеры\n"
                f"• ❔ Сказать что еще не знаете размер\n"
                f"• ◀️ Вернуться назад\n\n"
                f"Просто напишите размеры в чат или выберите вариант:",
                get_size_keyboard()
            )
            data['waiting_for_size_type'] = True
            return
            
        elif current_step == 2:
            # Размеры (с новой логикой)
            if waiting_for_size_type:
                # Пользователь выбрал вариант из клавиатуры
                if text == "📏 Я знаю точный размер":
                    send_message(
                        vk,
                        user_id,
                        f"📏 Укажите точные размеры кухни:\n\n"
                        f"Например:\n"
                        f"• 3х2.5м\n"
                        f"• Длина 4м, ширина 2м\n"
                        f"• 320х250см\n\n"
                        f"Просто напишите в чат:",
                        get_back_keyboard()
                    )
                    data['waiting_for_size_type'] = False
                    return
                    
                elif text == "❓ Знаю только приблизительно":
                    send_message(
                        vk,
                        user_id,
                        f"❓ Укажите приблизительные размеры:\n\n"
                        f"Например:\n"
                        f"• Примерно 3 на 2.5 метра\n"
                        f"• Небольшая кухня 6-7 кв.м\n"
                        f"• Комната 4х3 метра\n\n"
                        f"Опишите как можете:",
                        get_back_keyboard()
                    )
                    data['waiting_for_size_type'] = False
                    return
                    
                elif text == "❔ Еще не знаю размер":
                    data['form_data']['size'] = "Размер неизвестен, нужен замер"
                    data['current_step'] = 3
                    data['waiting_for_size_type'] = False
                    
                    send_message(
                        vk, 
                        user_id, 
                        f"✅ Размер: {data['form_data']['size']}\n\n"
                        f"3/3. Когда нужна кухня?",
                        get_deadline_keyboard()
                    )
                    return
                    
                else:
                    # Пользователь ввел размеры напрямую
                    data['form_data']['size'] = text
                    data['current_step'] = 3
                    data['waiting_for_size_type'] = False
                    
                    send_message(
                        vk, 
                        user_id, 
                        f"✅ Размеры: {text}\n\n"
                        f"3/3. Когда нужна кухня?",
                        get_deadline_keyboard()
                    )
                    return
            else:
                # Пользователь ввел размеры после выбора типа
                data['form_data']['size'] = text
                data['current_step'] = 3
                
                send_message(
                    vk, 
                    user_id, 
                    f"✅ Размеры: {text}\n\n"
                    f"3/3. Когда нужна кухня?",
                    get_deadline_keyboard()
                )
                return
            
        elif current_step == 3:
            # Сроки (последний вопрос перед телефоном)
            data['form_data']['deadline'] = text
            data['current_step'] = 4  # Шаг для телефона
            
            send_message(
                vk, 
                user_id, 
                f"✅ Срок: {text}\n\n"
                f"📞 Остался последний шаг!\n"
                f"Отправьте номер телефона для связи:\n\n"
                f"Напишите номер в чат (например, +79161234567)\n\n"
                f"Также можно:\n"
                f"◀️ Назад - чтобы изменить сроки\n"
                f"◀️ Отмена - чтобы отменить заявку",
                get_phone_final_keyboard()
            )
            return
            
    # ШКАФ (4 вопроса + телефон)
    elif form_type == 'ШКАФ' and 1 <= current_step <= 4:
        if text == "◀️ Отмена":
            cancel_form(user_id)
            send_message(vk, user_id, "❌ Заполнение формы отменено.", get_main_keyboard())
            return
            
        if current_step == 1:
            # Тип шкафа
            if text == "Другой вариант":
                send_message(
                    vk, 
                    user_id, 
                    f"📝 Укажите ваш вариант шкафа:\n"
                    f"Например: встроенный, комбинированный, с зеркалом и т.д.",
                    get_back_keyboard()
                )
                data['form_data']['type'] = "Другой вариант (ожидает уточнения)"
                data['waiting_for_custom_type'] = True
                return
            
            if data.get('waiting_for_custom_type'):
                # Пользователь ввел свой вариант
                data['form_data']['type'] = f"Другой вариант: {text}"
                data['waiting_for_custom_type'] = False
            else:
                data['form_data']['type'] = text
            
            data['current_step'] = 2
            
            send_message(
                vk, 
                user_id, 
                f"✅ Тип: {data['form_data']['type']}\n\n"
                f"2/4. Какие размеры шкафа?\n\n"
                f"Вы можете:\n"
                f"• 📏 Указать точные размеры (ширина, высота, глубина)\n"
                f"• ❓ Указать приблизительные размеры\n"
                f"• ❔ Сказать что еще не знаете размер\n"
                f"• ◀️ Вернуться назад\n\n"
                f"Просто напишите размеры в чат или выберите вариант:",
                get_size_keyboard()
            )
            data['waiting_for_size_type'] = True
            return
            
        elif current_step == 2:
            # Размеры шкафа (с новой логикой)
            if waiting_for_size_type:
                # Пользователь выбрал вариант из клавиатуры
                if text == "📏 Я знаю точный размер":
                    send_message(
                        vk,
                        user_id,
                        f"📏 Укажите точные размеры шкафа:\n\n"
                        f"Например:\n"
                        f"• Ширина 2м, высота 2.4м, глубина 60см\n"
                        f"• 200х240х60см\n"
                        f"• 2м в ширину, 2.4м в высоту\n\n"
                        f"Просто напишите в чат:",
                        get_back_keyboard()
                    )
                    data['waiting_for_size_type'] = False
                    return
                    
                elif text == "❓ Знаю только приблизительно":
                    send_message(
                        vk,
                        user_id,
                        f"❓ Укажите приблизительные размеры:\n\n"
                        f"Например:\n"
                        f"• Примерно 2 метра в ширину\n"
                        f"• Высота до потолка, ширина 1.5-2м\n"
                        f"• Небольшой шкаф 1.8х2.2м\n\n"
                        f"Опишите как можете:",
                        get_back_keyboard()
                    )
                    data['waiting_for_size_type'] = False
                    return
                    
                elif text == "❔ Еще не знаю размер":
                    data['form_data']['size'] = "Размер неизвестен, нужен замер"
                    data['current_step'] = 3
                    data['waiting_for_size_type'] = False
                    
                    send_message(
                        vk, 
                        user_id, 
                        f"✅ Размер: {data['form_data']['size']}\n\n"
                        f"3/4. Есть ли у вас дизайн-проект?",
                        get_design_project_keyboard()
                    )
                    return
                    
                else:
                    # Пользователь ввел размеры напрямую
                    data['form_data']['size'] = text
                    data['current_step'] = 3
                    data['waiting_for_size_type'] = False
                    
                    send_message(
                        vk, 
                        user_id, 
                        f"✅ Размеры: {text}\n\n"
                        f"3/4. Есть ли у вас дизайн-проект?",
                        get_design_project_keyboard()
                    )
                    return
            else:
                # Пользователь ввел размеры после выбора типа
                data['form_data']['size'] = text
                data['current_step'] = 3
                
                send_message(
                    vk, 
                    user_id, 
                    f"✅ Размеры: {text}\n\n"
                    f"3/4. Есть ли у вас дизайн-проект?",
                    get_design_project_keyboard()
                )
                return
            
        elif current_step == 3:
            # Дизайн-проект
            data['form_data']['design_project'] = text
            data['current_step'] = 4
            
            send_message(
                vk, 
                user_id, 
                f"✅ Дизайн-проект: {text}\n\n"
                f"4/4. Когда планируете покупку шкафа?",
                get_timeframe_keyboard()
            )
            return
            
        elif current_step == 4:
            # Сроки покупки (последний вопрос перед телефоном)
            data['form_data']['timeframe'] = text
            data['current_step'] = 5  # Шаг для телефона
            
            send_message(
                vk, 
                user_id, 
                f"✅ Срок покупки: {text}\n\n"
                f"📞 Остался последний шаг!\n"
                f"Отправьте номер телефона для связи:\n\n"
                f"Напишите номер в чат (например, +79161234567)\n\n"
                f"Также можно:\n"
                f"◀️ Назад - чтобы изменить сроки\n"
                f"◀️ Отмена - чтобы отменить заявку",
                get_phone_final_keyboard()
            )
            return
    
    # ========== ОБРАБОТКА ТЕЛЕФОНА ИЗ ОПРОСНИКА ==========
    
    # Обработка телефона для кухни
    if form_type == 'КУХНЯ' and current_step == 4:
        if text == "◀️ Назад":
            data['current_step'] = 3
            send_message(
                vk, 
                user_id, 
                f"3/3. Когда нужна кухня?\n\n"
                f"Текущий ответ: {data['form_data'].get('deadline', 'не выбран')}",
                get_deadline_keyboard()
            )
            return
            
        elif text == "◀️ Отмена":
            cancel_form(user_id)
            send_message(vk, user_id, "❌ Заполнение формы отменено.", get_main_keyboard())
            return
            
        elif is_valid_phone_number(text):
            # Обрабатываем номер телефона
            send_form_to_admin(vk, user_id, user_name, text, is_manual=True)
            return
        else:
            send_message(
                vk, 
                user_id, 
                "❌ Пожалуйста, введите корректный номер телефона или используйте кнопки.",
                get_phone_final_keyboard()
            )
            return
    
    # Обработка телефона для шкафа
    if form_type == 'ШКАФ' and current_step == 5:
        if text == "◀️ Назад":
            data['current_step'] = 4
            send_message(
                vk, 
                user_id, 
                f"4/4. Когда планируете покупку шкафа?\n\n"
                f"Текущий ответ: {data['form_data'].get('timeframe', 'не выбран')}",
                get_timeframe_keyboard()
            )
            return
            
        elif text == "◀️ Отмена":
            cancel_form(user_id)
            send_message(vk, user_id, "❌ Заполнение формы отменено.", get_main_keyboard())
            return
            
        elif is_valid_phone_number(text):
            # Обрабатываем номер телефона
            send_form_to_admin(vk, user_id, user_name, text, is_manual=True)
            return
        else:
            send_message(
                vk, 
                user_id, 
                "❌ Пожалуйста, введите корректный номер телефона или используйте кнопки.",
                get_phone_final_keyboard()
            )
            return
    
    # ========== ОБРАБОТКА ТЕЛЕФОНА ИЗ МЕНЮ ==========
    
    last_action = data.get('last_action')
    
    if last_action in ['callback', 'measure'] and is_valid_phone_number(text):
        # Это телефон из меню
        request_type = "ЗАКАЗ ЗВОНКА" if last_action == 'callback' else "ВЫЗОВ ЗАМЕРЩИКА"
        send_simple_request(vk, user_id, user_name, text, request_type, is_manual=True)
        return
    
    # ========== ОБРАБОТКА ОБЫЧНЫХ СООБЩЕНИЙ ==========
    
    # Кнопка "Назад в меню"
    if text == "◀️ Назад в меню":
        cancel_form(user_id)
        send_message(vk, user_id, "Главное меню:", get_main_keyboard())
        return
    
    # Основные кнопки меню
    elif text == "📞 Заказать звонок":
        data['last_action'] = 'callback'
        send_message(
            vk, 
            user_id, 
            f"📞 Заказать обратный звонок\n\n"
            f"{user_name}, наш менеджер перезвонит вам как можно скорее!\n\n"
            f"Отправьте номер телефона:\n"
            f"Просто напишите номер в чат",
            get_phone_keyboard()
        )
    
    elif text == "💰 Рассчитать стоимость":
        send_message(
            vk, 
            user_id, 
            f"💰 Рассчитать стоимость\n\n"
            f"{user_name}, выберите тип мебели для расчета:",
            get_calculate_keyboard()
        )
    
    elif text == "📸 Примеры работ":
        send_message(
            vk, 
            user_id, 
            f"📸 Примеры наших работ\n\n"
            f"{user_name}, посмотреть наши {COMPANY_INFO['completed_projects']} выполненных проектов подробнее вы можете на нашем сайте: sohokitchen.ru\n\n"
            f"Или в нашем фотоальбоме группы Сохо!\n\n"
            f"Контакты для связи:\n"
            f"+7 (499) 110-71-89\n"
            f"+7 (977) 984-66-96\n"
            f"+7 (925) 459-64-39",
            get_back_keyboard()
        )
    
    elif text == "📍 Контакты":
        send_message(
            vk, 
            user_id, 
            f"📍 Контакты кухонной фабрики Soho\n\n"
            f"📞 Телефон: {COMPANY_INFO['phone']}\n"
            f"📧 Email: {COMPANY_INFO['email']}\n"
            f"🌐 Сайт: {COMPANY_INFO['website']}\n"
            f"📱 Наша группа Telegram: {COMPANY_INFO['telegram']}\n"
            f"🏭 Адрес: {COMPANY_INFO['address']}\n"
            f"⏰ Часы работы: {COMPANY_INFO['work_hours']}",
            get_back_keyboard()
        )
    
    elif text == "👷 Вызвать замерщика":
        data['last_action'] = 'measure'
        send_message(
            vk, 
            user_id, 
            f"👷 Вызов замерщика\n\n"
            f"{user_name}, наш специалист свяжется с вами и назначит дату замера!\n\n"
            f"Что включает замер:\n"
            f"• Бесплатный 3д проект\n"
            f"• Советы по дизайну кухни и спецификация\n"
            f"• При заключении в первую встречу подарок\n\n"
            f"Отправьте номер для связи:\n"
            f"Просто напишите номер в чат",
            get_phone_keyboard()
        )
    
    elif text == "🎨 Кухня":
        # Начало опросника для кухни
        data['form_type'] = 'КУХНЯ'
        data['form_data'] = {}
        data['current_step'] = 1
        
        send_message(
            vk, 
            user_id, 
            f"🎨 Расчет стоимости кухни\n\n"
            f"{user_name}, ответьте на 3 вопроса для точного расчета.\n\n"
            f"1/3. Какая конфигурация кухни вам нужна?",
            get_kitchen_type_keyboard()
        )
    
    elif text == "🚪 Шкаф":
        # Начало опросника для шкафа
        data['form_type'] = 'ШКАФ'
        data['form_data'] = {}
        data['current_step'] = 1
        
        send_message(
            vk, 
            user_id, 
            f"🚪 Расчет стоимости шкафа\n\n"
            f"{user_name}, ответьте на 4 вопроса для точного расчета.\n\n"
            f"1/4. Какой тип шкафа вам нужен?",
            get_wardrobe_type_keyboard()
        )
    
    else:
        # Если это первое сообщение или непонятный текст
        if user_id not in user_data or data.get('form_type') is None:
            welcome_text = get_welcome_message(user_name)
            # Отправляем сообщение с фотографиями
            send_message_with_photos(vk, user_id, welcome_text, WELCOME_PHOTOS, get_main_keyboard())

def cancel_form(user_id):
    """Отмена заполнения формы"""
    if user_id in user_data:
        user_data[user_id] = {
            'form_type': None,
            'form_data': {},
            'current_step': 0,
            'waiting_for_custom_type': False,
            'waiting_for_size_type': False,  # Новое поле
            'last_action': None,
            'last_activity': datetime.now().timestamp(),
            'reminder_sent_1': False,
            'reminder_sent_2': False,
            'reminders_disabled': False
        }

def send_reminder_to_user(vk, user_id, reminder_number):
    """Отправка напоминания пользователю"""
    try:
        user_name = get_user_name(vk, user_id)
        
        # Получаем текст напоминания
        reminder_text = REMINDER_TEXTS.get(reminder_number, REMINDER_TEXTS[1])
        
        print(f"⏰ Отправка напоминания #{reminder_number} пользователю {user_id} ({user_name})")
        
        # Для второго напоминания отправляем без клавиатуры (последнее напоминание)
        if reminder_number == 2:
            send_message(
                vk,
                user_id,
                reminder_text
            )
        else:
            send_message(
                vk,
                user_id,
                reminder_text,
                get_main_keyboard()
            )
            
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки напоминания #{reminder_number} пользователю {user_id}: {e}")
        return False

def check_and_send_reminders(vk):
    """Проверка и отправка напоминаний неактивным пользователям"""
    if not REMINDER_ENABLED:
        return
    
    current_time = datetime.now().timestamp()
    print(f"🔍 Проверка напоминаний. Пользователей в базе: {len(user_data)}")
    
    for user_id, user_data_item in list(user_data.items()):
        try:
            # Пропускаем если напоминания отключены
            if user_data_item.get('reminders_disabled', False):
                continue
                
            last_activity = user_data_item.get('last_activity', 0)
            time_since_activity = current_time - last_activity
            
            # Первое напоминание через 6 часов
            if (time_since_activity >= REMINDER_INTERVAL_1 and 
                not user_data_item.get('reminder_sent_1', False)):
                
                if send_reminder_to_user(vk, user_id, 1):
                    user_data[user_id]['reminder_sent_1'] = True
                    print(f"✅ Отправлено первое напоминание пользователю {user_id}")
            
            # Второе напоминание через 24 часа
            elif (time_since_activity >= REMINDER_INTERVAL_2 and 
                  not user_data_item.get('reminder_sent_2', False)):
                
                if send_reminder_to_user(vk, user_id, 2):
                    user_data[user_id]['reminder_sent_2'] = True
                    user_data[user_id]['reminders_disabled'] = True  # Отключаем дальнейшие напоминания
                    print(f"✅ Отправлено второе напоминание пользователю {user_id}")
                    print(f"⚠️  Напоминания отключены для пользователя {user_id}")
        
        except Exception as e:
            print(f"❌ Ошибка проверки напоминаний для пользователя {user_id}: {e}")

# ========== ПОТОК ДЛЯ НАПОМИНАНИЙ ==========

def reminder_checker_thread(vk):
    """Поток для периодической проверки и отправки напоминаний"""
    print("⏰ Запуск системы напоминаний...")
    print(f"📅 Первое напоминание через {REMINDER_INTERVAL_1/3600} часов")
    print(f"📅 Второе напоминание через {REMINDER_INTERVAL_2/3600} часов")
    
    while True:
        try:
            check_and_send_reminders(vk)
            time.sleep(REMINDER_CHECK_INTERVAL)
        except Exception as e:
            print(f"❌ Ошибка в потоке напоминаний: {e}")
            time.sleep(60)  # Пауза при ошибке

# ========== ЗАПУСК БОТА ==========

def main():
    """Основная функция запуска бота"""
    print("=" * 60)
    print("🏭 VK Kitchen Bot запущен!")
    print("=" * 60)
    
    # Проверка переменных окружения
    if not VK_TOKEN or not GROUP_ID:
        print("❌ ERROR: Missing environment variables!")
        print(f"   VK_TOKEN: {'SET' if VK_TOKEN else 'MISSING'}")
        print(f"   GROUP_ID: {'SET' if GROUP_ID else 'MISSING'}")
        print(f"   ADMIN_ID: {ADMIN_ID}")
        return
    
    # Авторизация
    while True:  # Бесконечный цикл с переподключением
        try:
            vk_session = vk_api.VkApi(token=VK_TOKEN)
            vk = vk_session.get_api()
            
            # Long Poll
            longpoll = VkBotLongPoll(vk_session, GROUP_ID)
            
            print("✅ Успешное подключение к VK!")
            print(f"👤 Администратор: {ADMIN_ID}")
            print(f"⏰ Напоминания: {'ВКЛЮЧЕНЫ' if REMINDER_ENABLED else 'ВЫКЛЮЧЕНЫ'}")
            print("📸 Фотографии для приветствия:", WELCOME_PHOTOS)
            print("🤖 Бот слушает сообщения...")
            
            # Запуск потока для напоминаний
            if REMINDER_ENABLED:
                reminder_thread = threading.Thread(
                    target=reminder_checker_thread, 
                    args=(vk,), 
                    daemon=True
                )
                reminder_thread.start()
                print("✅ Система напоминаний запущена")
            
            # Основной цикл
            for event in longpoll.listen():
                try:
                    if event.type == VkBotEventType.MESSAGE_NEW:
                        if event.from_user:
                            user_id = event.message['from_id']
                            text = event.message['text']
                            
                            print(f"📩 Сообщение от {user_id}: {text[:50]}...")
                            handle_message(vk, user_id, text)
                            
                except Exception as e:
                    print(f"❌ Ошибка обработки сообщения: {e}")
                    
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            print("🔄 Переподключение через 10 секунд...")
            time.sleep(10)  # Ждем перед переподключением

if __name__ == "__main__":
    print("=" * 60)
    print("🏭 Запуск VK Kitchen Bot...")
    print("=" * 60)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)