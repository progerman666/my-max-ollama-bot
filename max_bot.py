# max_bot.py
import asyncio
import logging
import aiohttp
import os
from dotenv import load_dotenv
from maxapi import Bot, Dispatcher
from maxapi.types import MessageCreated
from maxapi.filters.command import CommandStart

# --- Загружаем переменные окружения из файла .env ---
load_dotenv()
MAX_BOT_TOKEN = os.getenv("MAX_BOT_TOKEN")

if not MAX_BOT_TOKEN:
    raise RuntimeError(
        "Переменная MAX_BOT_TOKEN не найдена. "
        "Проверьте, что файл .env существует и содержит строку MAX_BOT_TOKEN=..."
    )

# --- Настройки ---
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:latest"

# --- Логирование ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("max_bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# --- Инициализация ---
bot = Bot(token=MAX_BOT_TOKEN)
dp = Dispatcher()


# --- Обработчики ---

@dp.bot_started()
async def bot_started(event):
    await bot.send_message(
        chat_id=event.chat_id,
        text="Привет! Я локальный ИИ-бот на базе Ollama. Отправь мне любой текст."
    )


@dp.message_created(CommandStart())
async def cmd_start(event: MessageCreated):
    await event.message.answer(
        "Привет! Отправь мне любой вопрос — я отвечу через локальную модель."
    )


@dp.message_created()
async def handle_message(event: MessageCreated):
    user_text = event.message.body.text
    if not user_text:
        return

    # Показываем, что бот принял сообщение
    await event.message.answer("Секунду, думаю...")

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": user_text,
        "stream": False,
        "keep_alive": "10m"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OLLAMA_URL, json=payload, timeout=180) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    answer = data.get("response", "Ошибка: пустой ответ от модели.")
                    await event.message.answer(answer)
                else:
                    err_text = await resp.text()
                    logging.error(f"Ollama вернула {resp.status}: {err_text}")
                    await event.message.answer(f"Ошибка Ollama: {resp.status}")
    except asyncio.TimeoutError:
        logging.error("Ollama не ответила за 180 секунд")
        await event.message.answer("Модель думает слишком долго. Попробуйте ещё раз.")
    except Exception as e:
        logging.error(f"Ошибка при запросе к Ollama: {type(e).__name__}: {e}")
        await event.message.answer("Произошла внутренняя ошибка. Попробуйте позже.")


# --- Запуск ---

async def main():
    logging.info("Запуск MAX-бота...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем.")