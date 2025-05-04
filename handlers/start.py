from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from models import User

router = Router()

# INLINE MENU
def get_main_inline_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Переглянути профіль", callback_data="profile")],
            [InlineKeyboardButton(text="📛 Замовити іменну табличку", callback_data="nameplate")],
            [InlineKeyboardButton(text="📊 Історія відвідувань і оплат", callback_data="history")],
            [InlineKeyboardButton(text="⚙️ Налаштування та сповіщення", callback_data="settings")]
        ]
    )

# /start
@router.message(Command("start"))
async def start_handler(message: types.Message):
    User.get_or_create(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name
    )
    await message.answer(
        f"👋 Привіт, {message.from_user.full_name}!\nОсь твоє меню:",
        reply_markup=get_main_inline_menu()
    )

# Обробка натискань
@router.callback_query()
async def handle_menu_callback(callback: types.CallbackQuery):
    action = callback.data

    if action == "profile":
        user = User.get_by_tg_id(callback.from_user.id)
        text = f"👤 <b>Профіль</b>\n\n" \
               f"Ім’я: {user[3]}\n" \
               f"Нік: @{user[2]}\n" \
               f"Статус: {user[5]}\n" \
               f"Ігор відвідано: {user[6]}\n" \
               f"Оплачено: {user[7]}\n" \
               f"Бонуси: {user[8]}"
        await callback.message.edit_text(text, parse_mode="HTML")

    elif action == "nameplate":
        await callback.message.edit_text("📛 Форма замовлення таблички буде тут.")

    elif action == "history":
        await callback.message.edit_text("📊 Тут буде історія ігор та оплат.")

    elif action == "settings":
        await callback.message.edit_text("⚙️ Тут будуть налаштування та сповіщення.")

    await callback.answer()
