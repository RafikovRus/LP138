import os
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

# Загрузка переменных окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PRIZE_PATH = os.getenv("PRIZE_PATH", "/app/data/prize.json")
WINNERS_PATH = os.getenv("WINNERS_PATH", "/app/data/winners.json")

# Состояния для ConversationHandler
WAITING_FOR_TICKET = 1

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_prizes():
    """Загружает призы из JSON файла"""
    try:
        with open(PRIZE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("prizes", []), data.get("valid_tickets", [])
    except FileNotFoundError:
        logger.error(f"Файл {PRIZE_PATH} не найден!")
        return [], []

def save_prizes(prizes):
    """Сохраняет призы в JSON файл"""
    try:
        with open(PRIZE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["prizes"] = prizes
        with open(PRIZE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения призов: {e}")

def load_winners():
    """Загружает список победителей"""
    try:
        with open(WINNERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"winners": []}

def save_winner(winner_data):
    """Сохраняет информацию о победителе"""
    winners_data = load_winners()
    winners_data["winners"].append(winner_data)
    with open(WINNERS_PATH, "w", encoding="utf-8") as f:
        json.dump(winners_data, f, ensure_ascii=False, indent=2)

def is_ticket_used(ticket_code):
    """Проверяет, не использован ли уже билет"""
    winners_data = load_winners()
    return any(w.get("ticket_code") == ticket_code for w in winners_data["winners"])

def get_available_prizes(prizes):
    """Возвращает список доступных призов"""
    return [p for p in prizes if p["remaining"] > 0]

def draw_prize(prizes):
    """Розыгрыш приза с учётом веса"""
    available = get_available_prizes(prizes)
    if not available:
        return None
    
    # Веса для разных редкостей
    weights = {"common": 10, "rare": 3, "legendary": 1}
    
    weighted_prizes = []
    for prize in available:
        weight = weights.get(prize.get("rarity", "common"), 5)
        weighted_prizes.extend([prize] * weight)
    
    return random.choice(weighted_prizes)

# ===== ОБРАБОТЧИКИ КОМАНД =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главное меню с 3 кнопками"""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("ℹ️ Информация о проекте", callback_data="about")],
        [InlineKeyboardButton("🎁 Список призов", callback_data="prizes_list")],
        [InlineKeyboardButton("🎟️ Участвовать", callback_data="participate")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        f"✨ <b>Добро пожаловать, {user.mention_html()}!</b> ✨\n\n"
        f"🎯 <b>Благотворительная беспроигрышная лотерея</b>\n"
        f"Каждый участник гарантированно получает подарок!\n\n"
        f"📜 <b>Как участвовать:</b>\n"
        f"1️⃣ Нажмите кнопку «Участвовать»\n"
        f"2️⃣ Введите код вашего билета\n"
        f"3️⃣ Получите мгновенный результат розыгрыша\n\n"
        f"<i>Все собранные средства идут на благотворительность! ❤️</i>"
    )
    
    await update.message.reply_html(welcome_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "about":
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
            "<i>Спасибо, что вы с нами!</i>"
        )
        await query.edit_message_text(about_text, parse_mode="HTML")
    
    elif query.data == "prizes_list":
        prizes, _ = load_prizes()
        
        if not prizes:
            await query.edit_message_text(
                "😔 Информация о призах временно недоступна.",
                parse_mode="HTML"
            )
            return
        
        prizes_text = "🎁 <b>Список призов в лотерее:</b>\n\n"
        for prize in prizes:
            status = "✅" if prize["remaining"] > 0 else "❌"
            prizes_text += f"{status} <b>{prize['name']}</b>\n"
            prizes_text += f"   └ {prize['description']}\n"
            prizes_text += f"   └ Осталось: {prize['remaining']} из {prize['quantity']}\n\n"
        
        await query.edit_message_text(prizes_text, parse_mode="HTML")
    
    elif query.data == "participate":
        await query.edit_message_text(
            "🎟️ <b>Введите код вашего билета</b>\n\n"
            "Пожалуйста, отправьте код билета одним сообщением.\n"
            "Код должен быть в формате: <code>TICKET-2024-XXX</code>\n\n"
            "Для отмены отправьте /cancel",
            parse_mode="HTML"
        )
        return WAITING_FOR_TICKET

async def handle_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка введённого кода билета"""
    ticket_code = update.message.text.strip()
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Загружаем данные
    prizes, valid_tickets = load_prizes()
    
    # Проверка валидности кода
    if ticket_code not in valid_tickets:
        await update.message.reply_text(
            "❌ <b>Неверный код билета!</b>\n\n"
            "Пожалуйста, проверьте код и попробуйте снова.\n"
            "Если у вас нет билета, обратитесь к организаторам.\n\n"
            "Используйте /start для возврата в главное меню.",
            parse_mode="HTML"
        )
        return
    
    # Проверка, не использован ли уже билет
    if is_ticket_used(ticket_code):
        await update.message.reply_text(
            "⚠️ <b>Этот билет уже был использован!</b>\n\n"
            "Каждый билет даёт право только на один подарок.\n"
            "Используйте /start для возврата в главное меню.",
            parse_mode="HTML"
        )
        return
    
    # Проверка наличия призов
    available_prizes = get_available_prizes(prizes)
    if not available_prizes:
        await update.message.reply_text(
            "😔 <b>К сожалению, все подарки уже разобраны!</b>\n\n"
            "Спасибо за участие! Следите за новыми акциями.\n"
            "Используйте /start для возврата в главное меню.",
            parse_mode="HTML"
        )
        return
    
    # Розыгрыш приза
    prize = draw_prize(prizes)
    if not prize:
        await update.message.reply_text(
            "😔 Произошла ошибка при розыгрыше. Пожалуйста, попробуйте позже.",
            parse_mode="HTML"
        )
        return
    
    # Обновляем количество оставшихся призов
    for p in prizes:
        if p["id"] == prize["id"]:
            p["remaining"] -= 1
            break
    save_prizes(prizes)
    
    # Сохраняем информацию о победителе
    winner_info = {
        "user_id": user_id,
        "username": username,
        "ticket_code": ticket_code,
        "prize_name": prize["name"],
        "prize_code": prize["code"],
        "won_at": datetime.now().isoformat()
    }
    save_winner(winner_info)
    
    # Отправляем результат
    win_text = (
        f"🎉 <b>ПОЗДРАВЛЯЕМ!</b> 🎉\n\n"
        f"<b>Ваш подарок:</b> {prize['name']}\n"
        f"<b>Код приза:</b> <code>{prize['code']}</code>\n\n"
        f"📦 <b>Описание:</b> {prize['description']}\n\n"
        f"<b>Как получить подарок:</b>\n"
        f"Сообщите код приза нашему координатору:\n"
        f"📱 Telegram: @volunteer_contact\n"
        f"📧 Email: gift@charity-project.org\n\n"
        f"<i>Спасибо за участие в благотворительной лотерее! 💝</i>"
    )
    
    await update.message.reply_text(win_text, parse_mode="HTML")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отмена ввода кода"""
    await update.message.reply_text(
        "❌ Ввод кода отменён.\n"
        "Используйте /start для возврата в главное меню.",
        parse_mode="HTML"
    )

def main() -> None:
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не найден в переменных окружения!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Регистрация обработчика кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Регистрация обработчика сообщений для ввода кода
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ticket))
    
    logger.info("🤖 Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
