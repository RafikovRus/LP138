import os
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler

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

# ===== РАБОТА С ФАЙЛАМИ =====

def ensure_data_dir():
    """Создаёт папку data если её нет"""
    data_dir = Path(PRIZE_PATH).parent
    data_dir.mkdir(exist_ok=True)

def load_prizes():
    """Загружает призы из JSON файла"""
    ensure_data_dir()
    try:
        with open(PRIZE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("prizes", []), data.get("valid_tickets", [])
    except FileNotFoundError:
        logger.error(f"Файл {PRIZE_PATH} не найден!")
        return [], []

def save_prizes(prizes):
    """Сохраняет призы в JSON файл"""
    ensure_data_dir()
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
    ensure_data_dir()
    try:
        with open(WINNERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"winners": []}

def save_winner(winner_data):
    """Сохраняет информацию о победителе"""
    ensure_data_dir()
    winners_data = load_winners()
    winners_data["winners"].append(winner_data)
    with open(WINNERS_PATH, "w", encoding="utf-8") as f:
        json.dump(winners_data, f, ensure_ascii=False, indent=2)

def is_ticket_used(ticket_code):
    """Проверяет, не использован ли уже билет"""
    winners_data = load_winners()
    return any(w.get("ticket_code") == ticket_code for w in winners_data["winners"])

def get_user_prizes(user_id):
    """Возвращает список выигрышей пользователя"""
    winners_data = load_winners()
    user_wins = [w for w in winners_data["winners"] if w.get("user_id") == user_id]
    return user_wins

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
    """Команда /start - приветствие"""
    user = update.effective_user
    
    welcome_text = (
        f"✨ <b>Добро пожаловать в благотворительную лотерею, {user.mention_html()}!</b> ✨\n\n"
        f"🎯 Это <b>беспроигрышная лотерея</b> — каждый участник гарантированно получает подарок!\n\n"
        f"📜 <b>Доступные команды:</b>\n"
        f"• /info - информация о проекте\n"
        f"• /prize - список призов\n"
        f"• /participate - участвовать в лотерее\n"
        f"• /my_prizes - мои выигранные призы\n"
        f"• /donate - поддержать проект\n\n"
        f"<i>Все собранные средства идут на благотворительность! ❤️</i>"
    )
    
    await update.message.reply_html(welcome_text)

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /info - информация о проекте"""
    info_text = (
        "🌱 <b>О благотворительном проекте</b>\n\n"
        "Мы — <b>«Zerno. Зона первой помощи»</b> — благотворительный проект, "
        "который ... описание будет потом.\n\n"
        "🎯 <b>Наша миссия:</b>\n"
        "Сделать помощь доступной и понятной каждому.\n\n"
        "📊 <b>Результаты за 2024 год:</b>\n"
        "• Помогли 150+ семьям\n"
        "• Собрали 500 000 ₽ на лечение\n"
        "• Провели 20+ благотворительных акций\n\n"
        "🌐 <b>Наши проекты:</b>\n"
        "• @zerno_help — новости проекта\n"
        "• @help_center — центр помощи\n\n"
        "<i>Спасибо, что вы с нами!</i>"
    )
    
    await update.message.reply_html(info_text)

async def prize_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /prize - список призов"""
    prizes, _ = load_prizes()
    
    if not prizes:
        await update.message.reply_html("😔 Информация о призах временно недоступна.")
        return
    
    prizes_text = "🎁 <b>Список призов в лотерее:</b>\n\n"
    for prize in prizes:
        status = "✅" if prize["remaining"] > 0 else "❌"
        prizes_text += f"{status} <b>{prize['name']}</b>\n"
        prizes_text += f"   └ {prize['description']}\n"
        prizes_text += f"   └ Осталось: {prize['remaining']} из {prize['quantity']}\n\n"
    
    await update.message.reply_html(prizes_text)

async def my_prizes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /my_prizes - показать выигрыши пользователя"""
    user_id = update.effective_user.id
    user_prizes = get_user_prizes(user_id)
    
    if not user_prizes:
        await update.message.reply_html(
            "🎟️ <b>У вас пока нет выигрышей</b>\n\n"
            "Используйте команду /participate, чтобы участвовать в лотерее "
            "и получить свой первый подарок!"
        )
        return
    
    # Группируем призы по статусу получения
    pending_prizes = [p for p in user_prizes if not p.get("received", False)]
    received_prizes = [p for p in user_prizes if p.get("received", False)]
    
    text = "🎁 <b>Ваши выигранные призы</b>\n\n"
    
    if pending_prizes:
        text += "📦 <b>Ожидают получения:</b>\n"
        for i, prize in enumerate(pending_prizes, 1):
            won_date = datetime.fromisoformat(prize["won_at"]).strftime("%d.%m.%Y %H:%M")
            text += (
                f"{i}. <b>{prize['prize_name']}</b>\n"
                f"   📅 Выигран: {won_date}\n"
                f"   🎫 Код приза: <code>{prize['prize_code']}</code>\n"
                f"   🎟️ Билет: {prize['ticket_code']}\n\n"
            )
    
    if received_prizes:
        text += "✅ <b>Полученные призы:</b>\n"
        for i, prize in enumerate(received_prizes, 1):
            won_date = datetime.fromisoformat(prize["won_at"]).strftime("%d.%m.%Y %H:%M")
            received_date = datetime.fromisoformat(prize.get("received_at", prize["won_at"])).strftime("%d.%m.%Y")
            text += (
                f"{i}. <b>{prize['prize_name']}</b>\n"
                f"   📅 Выигран: {won_date}\n"
                f"   ✅ Получен: {received_date}\n\n"
            )
    
    if not pending_prizes and not received_prizes:
        text = "🎟️ <b>У вас пока нет выигрышей</b>\n\nИспользуйте команду /participate, чтобы участвовать в лотерее!"
    
    text += "\n<i>Для получения приза свяжитесь с координатором: @volunteer_contact</i>"
    
    await update.message.reply_html(text)

async def donate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /donate - поддержать проект"""
    donate_text = (
        "💝 <b>Поддержать проект «Zerno. Зона первой помощи»</b>\n\n"
        "Любая сумма помогает нам продолжать добрые дела!\n\n"
        "🔹 <b>Сделать пожертвование:</b>\n"
        "👉 <a href='https://pay.cloudtips.ru/p/b4eda1b6'>pay.cloudtips.ru/p/b4eda1b6</a>\n\n"
        "<i>Спасибо за вашу поддержку! 🙏</i>"
    )
    
    await update.message.reply_html(donate_text, disable_web_page_preview=False)

async def participate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Команда /participate - начало участия в лотерее"""
    await update.message.reply_html(
        "🎟️ <b>Введите код вашего билета</b>\n\n"
        "Пожалуйста, отправьте код билета одним сообщением.\n"
        "Код должен быть в формате: <code>TICKET-2024-XXX</code>\n\n"
        "Для отмены отправьте /cancel"
    )
    return WAITING_FOR_TICKET

async def handle_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка введённого кода билета"""
    ticket_code = update.message.text.strip()
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Загружаем данные
    prizes, valid_tickets = load_prizes()
    
    # Проверка валидности кода
    if ticket_code not in valid_tickets:
        await update.message.reply_html(
            "❌ <b>Неверный код билета!</b>\n\n"
            "Пожалуйста, проверьте код и попробуйте снова.\n"
            "Если у вас нет билета, обратитесь к организаторам.\n\n"
            "Используйте /start для возврата в главное меню."
        )
        return ConversationHandler.END
    
    # Проверка, не использован ли уже билет
    if is_ticket_used(ticket_code):
        await update.message.reply_html(
            "⚠️ <b>Этот билет уже был использован!</b>\n\n"
            "Каждый билет даёт право только на один подарок.\n"
            "Используйте /my_prizes для просмотра ваших выигрышей."
        )
        return ConversationHandler.END
    
    # Проверка наличия призов
    available_prizes = get_available_prizes(prizes)
    if not available_prizes:
        await update.message.reply_html(
            "😔 <b>К сожалению, все подарки уже разобраны!</b>\n\n"
            "Спасибо за участие! Следите за новыми акциями.\n"
            "Используйте /start для возврата в главное меню."
        )
        return ConversationHandler.END
    
    # Розыгрыш приза
    prize = draw_prize(prizes)
    if not prize:
        await update.message.reply_html(
            "😔 Произошла ошибка при розыгрыше. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END
    
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
        "won_at": datetime.now().isoformat(),
        "received": False  # статус получения приза
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
        f"📧 Email: gift@zerno-project.org\n\n"
        f"💡 <b>Совет:</b> Используйте команду /my_prizes, "
        f"чтобы в любой момент посмотреть все ваши выигранные призы.\n\n"
        f"<i>Спасибо за участие в благотворительной лотерее! 💝</i>"
    )
    
    await update.message.reply_html(win_text)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена ввода кода"""
    await update.message.reply_html(
        "❌ Ввод кода отменён.\n"
        "Используйте /start для возврата в главное меню."
    )
    return ConversationHandler.END

def main() -> None:
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не найден в переменных окружения!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("prize", prize_command))
    application.add_handler(CommandHandler("my_prizes", my_prizes_command))
    application.add_handler(CommandHandler("donate", donate_command))
    
    # ConversationHandler для команды participate
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("participate", participate_command)],
        states={
            WAITING_FOR_TICKET: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ticket)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    
    logger.info("🤖 Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
