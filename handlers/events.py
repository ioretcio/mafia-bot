from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from handlers.start import get_back_to_main_menu
from database import SessionLocal
from models import User, Game, Registration
from aiogram.utils.markdown import hbold, hitalic
from datetime import date

router = Router()

@router.callback_query(F.data == "upcoming_events")
async def show_upcoming_events(callback: types.CallbackQuery):
    session = SessionLocal()
    user = session.query(User).filter_by(tg_id=callback.from_user.id).first()
    games = (
        session.query(Game)
        .filter(Game.date >= date.today())
        .order_by(Game.date)
        .limit(5)
        .all()
    )
    if not games:
        await callback.message.edit_text("🔕 Наразі немає запланованих подій.", reply_markup=get_back_to_main_menu())
        await callback.answer()
        session.close()
        return

    await callback.message.delete()

    for game in games:
        reg_count = session.query(Registration).filter(Registration.game_id == game.id).count()
        is_registered = session.query(Registration).filter_by(game_id=game.id, user_id=user.id).first() is not None
        text = f"📅 {hbold(game.date)} о {hitalic(game.time)}\n🎮 {game.type}\n📍 {game.location}\n👥 Записано: {reg_count}/{game.player_limit}"

        buttons = []
        if not is_registered:
            buttons.append([InlineKeyboardButton(text="📥 Записатись", callback_data=f"signup:{game.date}_{game.time}")])
        else:
            buttons.append([InlineKeyboardButton(text="❌ Відмовитись", callback_data=f"unregister:{game.id}")])

        buttons.append([InlineKeyboardButton(text="👥 Переглянути гравців", callback_data=f"players:{game.id}")])

        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.answer(text, reply_markup=markup, parse_mode="HTML")

    await callback.message.answer("⬅️ Повернутись у меню", reply_markup=get_back_to_main_menu())
    await callback.answer()
    session.close()


@router.callback_query(lambda c: c.data.startswith("signup:"))
async def handle_signup(callback: types.CallbackQuery):
    session = SessionLocal()
    data = callback.data.split("signup:")[1]
    date_, time = data.split("_")

    game = session.query(Game).filter_by(date=date_, time=time).first()
    if not game:
        await callback.answer("⚠️ Гру не знайдено!", show_alert=True)
        session.close()
        return

    user = session.query(User).filter_by(tg_id=callback.from_user.id).first()
    if not user:
        await callback.answer("⚠️ Користувача не знайдено!", show_alert=True)
        session.close()
        return

    already_registered = session.query(Registration).filter_by(user_id=user.id, game_id=game.id).first()
    if already_registered:
        await callback.answer("ℹ️ Ви вже записані на цю гру.", show_alert=True)
        session.close()
        return

    reg_count = session.query(Registration).filter_by(game_id=game.id).count()
    if game.player_limit and reg_count >= game.player_limit:
        await callback.answer("❌ Місць більше немає.", show_alert=True)
        session.close()
        return

    registration = Registration(user_id=user.id, game_id=game.id, payment_type="pending", present=1)
    session.add(registration)
    session.commit()

    price = game.price or 0
    buttons = [
        [InlineKeyboardButton(text=f"💳 Оплатити {price} грн" if price else f"✅  Підтвердити", callback_data="pay_dummy")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ]
    text = "💸 Залишилось оплатити гру!" if price else "✅ Підтвердіть нижче."
    await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()
    session.close()


@router.callback_query(lambda c: c.data.startswith("players:"))
async def handle_show_players(callback: types.CallbackQuery):
    try:
        game_id_str = callback.data.split("players:")[1]
        game_id = int(game_id_str)
    except (IndexError, ValueError):
        await callback.answer("⚠️ Невірний формат ID події.", show_alert=True)
        return

    session = SessionLocal()
    regs = (
        session.query(Registration)
        .filter_by(game_id=game_id)
        .join(User, Registration.user_id == User.id)
        .with_entities(User.full_name, User.username)
        .all()
    )
    session.close()

    if not regs:
        text = "🔍 Поки що ніхто не записався."
    else:
        text = "👥 <b>Учасники гри:</b>\n\n"
        for i, (full_name, username) in enumerate(regs, 1):
            text += f"{i}. {full_name}"
            if username:
                text += f" (@{username})"
            text += "\n"

    await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(lambda c: c.data.startswith("unregister:"))
async def handle_unregister(callback: types.CallbackQuery):
    session = SessionLocal()
    game_id = int(callback.data.split("unregister:")[1])
    user = session.query(User).filter_by(tg_id=callback.from_user.id).first()
    if not user:
        await callback.answer("⚠️ Вас не знайдено в базі.", show_alert=True)
        session.close()
        return

    registration = session.query(Registration).filter_by(user_id=user.id, game_id=game_id).first()
    if registration:
        session.delete(registration)
        session.commit()
        await callback.answer("❌ Ви скасували свою участь.")
        await callback.message.answer("Ваша реєстрація скасована.")
    else:
        await callback.answer("⚠️ Ви не були записані на цю гру.", show_alert=True)
    session.close()
