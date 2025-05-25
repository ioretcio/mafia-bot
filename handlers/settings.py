from aiogram import Router, types, F
from handlers.start import get_back_to_main_menu
from utils import safe_edit_or_send


router = Router()

@router.callback_query(F.data == "nameplate")
async def handle_nameplate(callback: types.CallbackQuery):
    await safe_edit_or_send(
        callback.message,
        "📛 Форма замовлення таблички буде тут.",
        reply_markup=get_back_to_main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "history")
async def handle_history(callback: types.CallbackQuery):
    await safe_edit_or_send(
        callback.message,
        "📊 Тут буде історія ігор та оплат.",
        reply_markup=get_back_to_main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "settings")
async def handle_settings(callback: types.CallbackQuery):
    await safe_edit_or_send(
        callback.message,
        "⚙️ Тут будуть налаштування та сповіщення.",
        reply_markup=get_back_to_main_menu()
    )
    await callback.answer()
