from aiogram import Router, types, F
from handlers.start import get_back_to_main_menu

router = Router()

@router.callback_query(F.data == "nameplate")
async def handle_nameplate(callback: types.CallbackQuery):
    await callback.message.answer(
        "📛 Форма замовлення таблички буде тут.",
        reply_markup=get_back_to_main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "history")
async def handle_history(callback: types.CallbackQuery):
    await callback.message.answer(
        "📊 Тут буде історія ігор та оплат.",
        reply_markup=get_back_to_main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "settings")
async def handle_settings(callback: types.CallbackQuery):
    await callback.message.answer(
        "⚙️ Тут будуть налаштування та сповіщення.",
        reply_markup=get_back_to_main_menu()
    )
    await callback.answer()
