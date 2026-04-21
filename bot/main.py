import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from database import create_pool
from handlers import client, admin

load_dotenv()

MIJOZ_BOT_TOKEN = os.getenv("MIJOZ_BOT_TOKEN")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")

WORK_START = int(os.getenv("WORK_START", 8))
WORK_END = int(os.getenv("WORK_END", 20))

async def main():
    # Database ulanish
    await create_pool()

    # Botlar
    mijoz_bot = Bot(token=MIJOZ_BOT_TOKEN)
    admin_bot = Bot(token=ADMIN_BOT_TOKEN)

    # Dispatcherlar
    mijoz_dp = Dispatcher(storage=MemoryStorage())
    admin_dp = Dispatcher(storage=MemoryStorage())

    # Handlerlarni ulash
    client.register(mijoz_dp)
    admin.register(admin_dp)

    print("🚀 Botlar ishga tushdi!")

    # Botlarni parallel ishga tushirish
    await asyncio.gather(
        mijoz_dp.start_polling(mijoz_bot),
        admin_dp.start_polling(admin_bot),
    )

if __name__ == "__main__":
    asyncio.run(main())