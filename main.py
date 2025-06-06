import asyncio
from aiogram import Bot, Dispatcher
from utils.config import BOT_TOKEN
from models.database import init_db
from dotenv import load_dotenv

from handlers import start_router, profile_router, events_router, settings_router

dp = Dispatcher()
dp.include_router(start_router)
dp.include_router(profile_router)
dp.include_router(events_router)
dp.include_router(settings_router)

load_dotenv()
import asyncio
import threading

main_loop = asyncio.new_event_loop()


def start_main_loop():
    asyncio.set_event_loop(main_loop)
    main_loop.run_forever()
threading.Thread(target=start_main_loop, daemon=True).start()


async def main():
    init_db()

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in .env file")

    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
