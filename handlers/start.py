from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User
from utils import safe_edit_or_send
from aiogram import F

router = Router()


def get_back_to_main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Головне меню", callback_data="main_menu")]]
    )




@router.callback_query(F.data.startswith("main_menu"))
async def handle_main_menu(callback: types.CallbackQuery):
    # Парсимо ID для видалення
    parts = callback.data.split("_")[2:]  # все після main_menu_
    for part in parts:
        try:
            msg_id = int(part)
            await callback.bot.delete_message(callback.message.chat.id, msg_id)
        except Exception as e:
            print(f"❌ Не вдалося видалити {part}: {e}")

    # Редагуємо поточне
    await safe_edit_or_send(
        callback.message,
        f"👋 Привіт, {callback.from_user.full_name}!",
        reply_markup=get_main_inline_menu()
    )
    await callback.answer()



def get_main_inline_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Переглянути профіль", callback_data="profile")],
            [InlineKeyboardButton(text="📛 Замовити іменну табличку", callback_data="nameplate")],
            [InlineKeyboardButton(text="📊 Історія відвідувань і оплат", callback_data="history")],
            [InlineKeyboardButton(text="⚙️ Налаштування та сповіщення", callback_data="settings")],
            [InlineKeyboardButton(text="📅 Заплановані івенти", callback_data="upcoming_events")]
        ]
    )


@router.message(Command("start"))
async def start_handler(message: types.Message):
    User.get_or_create(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name
    )
    await message.answer(
        f"👋 Привіт, {message.from_user.full_name}!",
        reply_markup=get_main_inline_menu()
    )