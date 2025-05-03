from aiogram import Router, types
from models import User

router = Router()

@router.message(commands=["start"])
async def start_handler(msg: types.Message):
    User.get_or_create(msg.from_user.id, msg.from_user.username, msg.from_user.full_name)
    await msg.answer(f"Привіт, {msg.from_user.full_name}!\nТи доданий до бази.")