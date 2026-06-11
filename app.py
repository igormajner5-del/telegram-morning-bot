import asyncio
import os
import threading
from datetime import datetime
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
USER_ID = int(os.getenv("USER_ID", 0))

# Проверка, что токен загрузился
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден в файле .env")
    exit(1)
if not USER_ID:
    print("❌ ОШИБКА: USER_ID не найден в файле .env")
    exit(1)

print(f"✅ Токен загружен: {BOT_TOKEN[:10]}...")
print(f"✅ USER_ID: {USER_ID}")

# Создаем Flask приложение
app = Flask(__name__)

# Создаем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === БАЗА ДАННЫХ (в памяти) ===
tasks = [
    {"id": 1, "text": "Выпить стакан воды", "completed": False},
    {"id": 2, "text": "Сделать зарядку", "completed": False},
    {"id": 3, "text": "Проверить почту", "completed": False},
]


# === КОМАНДЫ БОТА ===
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "🌅 Привет! Я утренний помощник!\n\n"
        "/schedule - показать дела\n"
        "/add <дело> - добавить дело\n"
        "/done <id> - отметить выполненным"
    )


@dp.message(Command("schedule"))
async def show_tasks(message: types.Message):
    if not tasks:
        await message.answer("🎉 Нет дел на сегодня!")
        return
    msg = "📋 Твои дела:\n"
    for t in tasks:
        status = "✅" if t["completed"] else "⭕️"
        msg += f"{status} {t['id']}. {t['text']}\n"
    await message.answer(msg)


@dp.message(Command("add"))
async def add_task(message: types.Message):
    text = message.text.replace("/add", "").strip()
    if text:
        new_id = max([t["id"] for t in tasks]) + 1 if tasks else 1
        tasks.append({"id": new_id, "text": text, "completed": False})
        await message.answer(f"✅ Добавлено: {text}")
    else:
        await message.answer("Напиши: /add купить молоко")


@dp.message(Command("done"))
async def done_task(message: types.Message):
    try:
        task_id = int(message.text.replace("/done", "").strip())
        for task in tasks:
            if task["id"] == task_id:
                task["completed"] = True
                await message.answer(f"✅ Дело #{task_id} выполнено!")
                return
        await message.answer(f"❌ Дело #{task_id} не найдено")
    except:
        await message.answer("Напиши: /done 1")


# === УТРЕННЕЕ УВЕДОМЛЕНИЕ ===
async def send_morning_message():
    """Отправляет утреннее приветствие"""
    if not tasks:
        await bot.send_message(USER_ID, "🌅 Доброе утро! На сегодня дел нет, отдыхай! 🎉")
        return

    msg = "🌅 Доброе утро! ☀️\n\n📋 Что нужно сделать сегодня:\n"
    for t in tasks:
        if not t["completed"]:
            msg += f"• {t['text']}\n"

    if msg == "🌅 Доброе утро! ☀️\n\n📋 Что нужно сделать сегодня:\n":
        msg += "Всё уже сделано! Отличная работа! ✅"

    await bot.send_message(USER_ID, msg)


# === ИСПРАВЛЕННЫЙ ПЛАНИРОВЩИК ===
async def scheduler_loop():
    """Планировщик утренних уведомлений (работает в том же цикле)"""
    print("⏰ Планировщик утренних уведомлений запущен")
    last_sent = None  # Чтобы не отправлять дважды в минуту

    while True:
        now = datetime.now()
        # Проверяем, не наступило ли 7 утра и не отправляли ли уже
        if now.hour == 3 and now.minute == 51 and last_sent != now.date():
            print("🔔 Отправляю утреннее уведомление...")
            try:
                await send_morning_message()
                last_sent = now.date()
                print("✅ Утреннее уведомление отправлено!")
            except Exception as e:
                print(f"❌ Ошибка при отправке: {e}")

        await asyncio.sleep(30)  # Проверяем каждые 30 секунд


# === ЗАПУСК ВСЕГО В ОДНОМ ЦИКЛЕ ===
async def main():
    """Главная функция, запускает и бота, и планировщик"""
    # Запускаем планировщик как отдельную задачу
    scheduler_task = asyncio.create_task(scheduler_loop())

    # Запускаем бота (это блокирующая операция)
    print("🤖 Бот запущен и слушает команды...")

    # Запускаем оба процесса параллельно
    await asyncio.gather(
        dp.start_polling(bot),
        scheduler_task
    )


# === FLASK ДЛЯ RENDER ===
@app.route('/')
def health_check():
    return "Bot is running!", 200


# === ТОЧКА ВХОДА ===
if __name__ == "__main__":
    # Запускаем Flask в отдельном потоке (он не мешает asyncio)
    def run_flask():
        port = int(os.getenv("PORT", 5000))
        print(f"🚀 Flask сервер запущен на порту {port}")
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Запускаем основную asyncio программу
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")