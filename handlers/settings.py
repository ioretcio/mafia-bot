from aiogram import Router, types, F
from handlers.start import get_back_to_main_menu
from utils import safe_edit_or_send
from models.game import Game
from database import SessionLocal
from models.payment import Payment

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
    user_id = callback.from_user.id
    session = SessionLocal()

    # Отримуємо користувача
    from models.user import User
    user = session.query(User).filter_by(tg_id=user_id).first()

    if not user:
        await callback.answer("❌ Користувача не знайдено", show_alert=True)
        session.close()
        return

    # Отримуємо платежі
    payments = Payment.get_user_payments(user.id)

    if not payments:
        await safe_edit_or_send(
            callback.message,
            "📭 Ви ще не здійснювали оплат.",
            reply_markup=get_back_to_main_menu()
        )
        await callback.answer()
        session.close()
        return

    # Формуємо список оплат
    lines = ["📊 <b>Історія оплат:</b>\n"]
    for p in payments:
        game = session.query(Game).filter_by(id=p.game_id).first() if p.game_id else None
        game_info = f"{game.date} {game.time}" if game else "—"
        lines.append(
            f"• {p.date.strftime('%Y-%m-%d %H:%M')} — <b>{p.amount} грн</b> — {p.status.upper()} — {game_info}"
        )

    text = "\n".join(lines)

    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=get_back_to_main_menu()
    )
    await callback.answer()
    session.close()


@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(callback: types.CallbackQuery):
    session = SessionLocal()
    from models.user import User
    user = session.query(User).filter_by(tg_id=callback.from_user.id).first()

    if not user:
        await callback.answer("❌ Користувача не знайдено", show_alert=True)
        session.close()
        return

    user.receive_notifications = not user.receive_notifications
    session.commit()
    session.close()

    await callback.answer("🔁 Стан розсилки змінено.")
    # Повертаємо назад до налаштувань
    await handle_settings(callback)


@router.callback_query(F.data == "settings")
async def handle_settings(callback: types.CallbackQuery):
    session = SessionLocal()
    from models.user import User
    user = session.query(User).filter_by(tg_id=callback.from_user.id).first()

    if not user:
        await callback.answer("❌ Користувача не знайдено", show_alert=True)
        session.close()
        return

    status = "✅ Так" if user.receive_notifications else "❌ Ні"
    text = f"⚙️ <b>Налаштування</b>\n\nОтримувати сповіщення про ігри та події: {status}"

    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(
            text="🔔 Змінити стан розсилки",
            callback_data="toggle_notifications"
        )],
        [types.InlineKeyboardButton(text="⬅️ Головне меню", callback_data="main_menu")]
    ])

    await safe_edit_or_send(callback.message, text, reply_markup=markup)
    await callback.answer()
    session.close()