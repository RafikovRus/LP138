import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Список призов
PRIZES = [
    {"name": "Сладкий новогодний набор", "description": "Коробка конфет и печенья", "available": 10},
    {"name": "Магнит с логотипом проекта", "description": "Сувенирный магнит", "available": 25},
    {"name": "Электронная книга о благотворительности", "description": "PDF-сборник историй", "available": 15},
    {"name": "Брендированная кружка", "description": "Керамическая кружка", "available": 5},
    {"name": "Сертификат в книжный магазин", "description": "Сертификат на 500 руб", "available": 3},
    {"name": "Главный приз — планшет", "description": "Планшет для учёбы", "available": 1},
]

# Хранилище выигрышей пользователей
user_wins = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start - приветствие и описание бота"""
    user = update.effective_user
    
    # Текст приветствия с описанием бота
    welcome_text = (
        f"✨ <b>Добро пожаловать, {user.mention_html()}!</b> ✨\n\n"
        f"🎯 <b>О боте:</b>\n"
        f"Это бот для <b>беспроигрышной благотворительной лотереи</b>.\n"
        f"Каждый участник гарантированно получает подарок!\n\n"
        f"📜 <b>Как участвовать:</b>\n"
        f"1️⃣ Нажмите кнопку «Участвовать в лотерее»\n"
        f"2️⃣ Получите мгновенный результат розыгрыша\n"
        f"3️⃣ Заберите свой подарок (инструкция придёт с выигрышем)\n\n"
        f"🎁 <b>Что можно выиграть?</b>\n"
        f"• Сладкие подарки\n"
        f"• Сувениры с символикой проекта\n"
        f"• Полезные призы (книги, сертификаты)\n"
        f"• Главный приз — <b>планшет!</b>\n\n"
        f"❤️ <b>О проекте:</b>\n"
        f"Все средства от лотереи идут на благотворительность — "
        f"помощь детям и пожилым людям.\n\n"
        f"Нажмите на кнопку ниже, чтобы получить свой подарок! 🎉"
    )
    
    await update.message.reply_html(
        welcome_text,
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "participate":
        # Проверяем, не участвовал ли пользователь уже (можно убрать если нужно много раз)
        if user_id in user_wins:
            await query.edit_message_text(
                "⚠️ <b>Вы уже участвовали в лотерее!</b>\n\n"
                f"Вы выиграли: <b>{user_wins[user_id]['prize']}</b>\n\n"
                "Один человек может участвовать только один раз.\n"
                "Но вы можете помочь проекту, нажав кнопку «Поддержать проект».",
                parse_mode="HTML"
            )
            return
        
        # Розыгрыш приза с учётом веса
        available_prizes = [p for p in PRIZES if p["available"] > 0]
        
        if not available_prizes:
            await query.edit_message_text(
                "😔 <b>К сожалению, все подарки уже разобраны!</b>\n\n"
                "Спасибо за участие! Следите за новыми акциями.\n\n"
                "Вы можете поддержать наш проект кнопкой ниже.",
                parse_mode="HTML"
            )
            return
        
        # Простой случайный выбор (можно усложнить весами)
        import random
        prize = random.choice(available_prizes)
        
        # Уменьшаем количество доступных призов
        for p in PRIZES:
            if p["name"] == prize["name"]:
                p["available"] -= 1
                break
        
        # Сохраняем выигрыш пользователя
        user_wins[user_id] = {
            "prize": prize["name"],
            "description": prize["description"],
            "code": f"GIFT-{random.randint(10000, 99999)}"
        }
        
        # Сообщение о выигрыше
        win_text = (
            f"🎉 <b>ПОЗДРАВЛЯЕМ!</b> 🎉\n\n"
            f"<b>Ваш подарок:</b> {prize['name']}\n"
            f"<b>Код приза:</b> <code>{user_wins[user_id]['code']}</code>\n\n"
            f"📦 <b>Описание:</b> {prize['description']}\n\n"
            f"<b>Как получить подарок:</b>\n"
            f"Сообщите код приза нашему координатору:\n"
            f"📱 Telegram: @volunteer_contact\n"
            f"📧 Email: gift@charity-project.org\n\n"
            f"<i>Спасибо, что помогаете делать добрые дела! 💝</i>"
        )
        
        await query.edit_message_text(win_text, parse_mode="HTML")
    
    elif query.data == "prizes_list":
        # Формируем список призов
        prizes_text = "🎁 <b>Список призов в лотерее:</b>\n\n"
        for prize in PRIZES:
            status = "✅" if prize["available"] > 0 else "❌"
            prizes_text += f"{status} <b>{prize['name']}</b>\n"
            prizes_text += f"   └ {prize['description']} (осталось: {prize['available']})\n"
        
        prizes_text += "\n<i>Все подарки гарантированно вручаются победителям!</i>"
        
        # Добавляем кнопку возврата
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(prizes_text, parse_mode="HTML", reply_markup=reply_markup)
    
    elif query.data == "about":
        about_text = (
            "🌱 <b>О благотворительном проекте</b>\n\n"
            "Мы — <b>«Доброе сердце»</b> — благотворительный фонд, "
            "который помогает детям-сиротам и пожилым людям.\n\n"
            "🎯 <b>Наша миссия:</b>\n"
            "Сделать помощь доступной и понятной каждому.\n\n"
            "📊 <b>Результаты за 2024 год:</b>\n"
            "• Помогли 150+ семьям\n"
            "• Собрали 500 000 ₽ на лечение\n"
            "• Провели 20+ благотворительных акций\n\n"
            "🌐 <b>Наши проекты:</b>\n"
            "• @charity_news — новости фонда\n"
            "• @help_center — центр помощи\n\n"
            "<i>Спасибо, что вы с нами!</i>"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(about_text, parse_mode="HTML", reply_markup=reply_markup)
    
    elif query.data == "donate":
        donate_text = (
            "💝 <b>Поддержать проект</b>\n\n"
            "Любая сумма помогает нам продолжать добрые дела!\n\n"
            "<b>Способы поддержки:</b>\n"
            "🔹 <b>Банковская карта:</b>\n"
            "   <code>1234 5678 9012 3456</code>\n"
            "   (Доброе сердце)\n\n"
            "🔹 <b>СБП (Система быстрых платежей):</b>\n"
            "   📞 +7 (912) 345-67-89\n"
            "   <i>Телефон привязан к фонду</i>\n\n"
            "🔹 <b>На сайте:</b>\n"
            "   <a href='https://charity-project.org/donate'>charity-project.org/donate</a>\n\n"
            "🔹 <b>Подписка в Telegram:</b>\n"
            "   @charity_donations_bot\n\n"
            "<b>🇷🇺 Налоговый вычет:</b>\n"
            "Все пожертвования принимаются официально — вы получите документы для возврата 13% налога.\n\n"
            "<i>Спасибо за вашу доброту! 🙏</i>"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(donate_text, parse_mode="HTML", reply_markup=reply_markup)
    
    elif query.data == "back_to_menu":
        # Возвращаем главное меню
        keyboard = [
            [InlineKeyboardButton("🎁 Участвовать в лотерее", callback_data="participate")],
            [InlineKeyboardButton("📋 Список призов", callback_data="prizes_list")],
            [InlineKeyboardButton("ℹ️ О проекте", callback_data="about")],
            [InlineKeyboardButton("🙏 Поддержать проект", callback_data="donate")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "✨ <b>Главное меню</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=reply_markup
        )

async def prize_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /prize - показать список призов"""
    prizes_text = "🎁 <b>Доступные призы:</b>\n\n"
    for prize in PRIZES:
        if prize["available"] > 0:
            prizes_text += f"• <b>{prize['name']}</b>\n"
            prizes_text += f"  {prize['description']} (осталось: {prize['available']})\n\n"
    
    if not any(p["available"] > 0 for p in PRIZES):
        prizes_text = "😔 К сожалению, все призы уже разобраны!"
    
    await update.message.reply_html(prizes_text)

def main() -> None:
    """Запуск бота"""
    application = Application.builder().token("8735371477:AAE1dRwtNTR4Uui9QdNgUV5Cu1a0TcjUfQs").build()

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("prize", prize_command))
    
    # Регистрация обработчика кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Запуск бота
    print("🤖 Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
