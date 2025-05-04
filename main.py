import asyncio
from aiogram import Bot, Dispatcher
from handlers import start
from config import BOT_TOKEN
from db import init_db
from dotenv import load_dotenv

load_dotenv()

async def main():
    init_db()

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in .env file")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(start.router)

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
