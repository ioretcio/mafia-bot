from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from handlers.start import get_back_to_main_menu
from models.database import SessionLocal
from models.user import User
from models.game import Game
from models.registration import Registration
from models.payment import Payment
from datetime import date
from utils.wayforpay_client import WayForPayClient
from utils.utils import safe_edit_or_send
from PIL import Image
from io import BytesIO
import os
from time import time
from datetime import datetime, timedelta, time as dtime




from datetime import datetime
from zoneinfo import ZoneInfo



router = Router()
wfp = WayForPayClient()

class EditStates(StatesGroup):
    awaiting_new_username = State()
    awaiting_topup_amount = State()
    confirming_balance_payment = State()

@router.callback_query(F.data == "upcoming_events")
async def show_upcoming_events(callback: types.CallbackQuery):
    session = SessionLocal()
    user = session.query(User).filter_by(tg_id=callback.from_user.id).first()
    games = (
        session.query(Game)
        .filter(Game.date >= date.today())
        .filter(Game.is_send == True)
        .order_by(Game.date)
        .limit(5)
        .all()
    )
    if not games:
        await callback.message.edit_text("🔕 Наразі немає запланованих подій.", reply_markup=get_back_to_main_menu())
        await callback.answer()
        session.close()
        return

    message_ids = []
    for idx, game in enumerate(games):
        reg_count = session.query(Registration).filter(Registration.game_id == game.id).count()
        is_registered = session.query(Registration).filter_by(game_id=game.id, user_id=user.id).first() is not None

        text = f"📅 <b>{game.date}</b> о <i>{game.time}</i>\n🎮 {game.type}\n📍 {game.location}\n👥 Записано: {reg_count}/{game.player_limit}"

        buttons = []
        if not is_registered:
            buttons.append([InlineKeyboardButton(text="📥 Записатись", callback_data=f"signup:{game.id}")])
        else:
            buttons.append([InlineKeyboardButton(text="❌ Відмовитись", callback_data=f"unregister:{game.id}")])
        buttons.append([InlineKeyboardButton(text="👥 Переглянути гравців", callback_data=f"players:{game.id}")])

        if idx == len(games) - 1:
            to_delete = "_".join(f"{mid}" for mid in message_ids)
            back_callback = f"main_menu_{to_delete}"
            buttons.append([InlineKeyboardButton(text="⬅️ Повернутись у меню", callback_data=back_callback)])

        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        if idx == 0:
            msg = await safe_edit_or_send(callback.message, text, reply_markup=markup, parse_mode="HTML")
            message_ids.append(msg.message_id)
        else:
            msg = await callback.message.answer(text, reply_markup=markup, parse_mode="HTML")
            message_ids.append(msg.message_id)

    session.close()

@router.callback_query(lambda c: c.data.startswith("signup:"))
async def handle_signup(callback: types.CallbackQuery, state: FSMContext):
    session = SessionLocal()
    user = session.query(User).filter_by(tg_id=callback.from_user.id).first()
    game_id = int(callback.data.split("signup:")[1])
    game = session.query(Game).get(game_id)
    if not game:
        await callback.answer("⚠️ Гру не знайдено!", show_alert=True)
        session.close()
        return

    reg_count = session.query(Registration).filter_by(game_id=game.id).count()
    if game.player_limit and reg_count >= game.player_limit:
        await callback.answer("❌ Місць більше немає.", show_alert=True)
        session.close()
        return

    if user.balance >= game.price:
        await state.set_data({"game_id": game.id, "amount": game.price})
        await callback.message.answer(f"🔒 Підтвердити оплату {game.price} грн з балансу?", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Так, підтверджую", callback_data="confirm_balance_payment")],
            [InlineKeyboardButton(text="⬅️ Скасувати", callback_data="main_menu")]
        ]))
        await state.set_state(EditStates.confirming_balance_payment)
    else:
        diff = game.price - user.balance
        order_reference =f"inv_{user.id}_{game.id}_{int(time())}"


        invoice = wfp.create_invoice(order_reference=order_reference, amount=int(diff), product_name="Game Registration")
        payment = Payment(
            user_id=user.id,
            game_id=game.id,
            amount=int(diff),
            payment_type="card",
            status="pending",
            order_reference=order_reference
        )
        session.add(payment)
        session.commit()

        invoice_url = invoice.get("invoiceUrl")
        buttons = [
            [InlineKeyboardButton(text="💳 Перейти до оплати", url=invoice_url, callback_data="...")],
            [InlineKeyboardButton(text="🔁 Перевірити статус", callback_data=f"check_payment:{order_reference}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
        ]
        await callback.message.answer(f"💸 Вам не вистачає {diff} грн. Поповніть рахунок та підтвердьте оплату.\nРаджу поповнювати рахунок наперед в особисому кабінеті.✨", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

    session.close()
    await callback.answer()

@router.callback_query(F.data == "confirm_balance_payment", StateFilter(EditStates.confirming_balance_payment))
async def confirm_balance_payment(callback: types.CallbackQuery, state: FSMContext):
    session = SessionLocal()
    user = session.query(User).filter_by(tg_id=callback.from_user.id).first()
    data = await state.get_data()
    game_id = data.get("game_id")
    amount = data.get("amount")

    if not user or not game_id or not amount:
        await callback.message.answer("⚠️ Неможливо завершити оплату.")
        await state.clear()
        session.close()
        return

    game = session.query(Game).get(game_id)
    if user.balance < amount:
        await callback.message.answer("❌ Недостатньо коштів на балансі.")
        await state.clear()
        session.close()
        return

    user.balance -= amount
    registration = Registration(user_id=user.id, game_id=game.id, payment_type="balance")
    session.add(registration)
    session.commit()
    await callback.message.answer("✅ Ви успішно зареєстровані на гру! Сума списана з балансу.")
    await state.clear()
    session.close()
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("check_payment:"))
async def check_payment_status(callback: types.CallbackQuery):
    order_reference = callback.data.split("check_payment:")[1]
    result = wfp.check_payment_status(order_reference)
    status = result.get("transactionStatus")

    session = SessionLocal()
    payment = session.query(Payment).filter_by(order_reference=order_reference).first()
    user = session.query(User).get(payment.user_id)
    game = session.query(Game).get(payment.game_id)

    if status == "Approved":
        payment.status = "paid"
        user.balance += payment.amount
        user.balance -= game.price
        registration = Registration(user_id=user.id, game_id=game.id, payment_type="balance")
        session.add(registration)
        session.commit()
        await callback.message.answer("✅ Оплату підтверджено та реєстрацію завершено!")
    elif status == "Pending":
        await callback.answer("⏳ Оплата ще очікується...", show_alert=True)
    else:
        await callback.answer(f"❌ Статус оплати: {status}", show_alert=True)

    session.close()
    await callback.answer()



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

    game = session.query(Game).get(game_id)
    if not game:
        await callback.answer("⚠️ Гру не знайдено.", show_alert=True)
        session.close()
        return

    # Поточний київський час
    kyiv_now = datetime.now(ZoneInfo("Europe/Kyiv"))
    print(f"Поточний час Київ: {kyiv_now}")
    # Граничний дедлайн — 21:00 попереднього дня
    game_date = datetime.strptime(game.date, "%Y-%m-%d").date()
    game_datetime = datetime.combine(game_date, dtime(hour=21), tzinfo=ZoneInfo("Europe/Kyiv"))

    unregister_deadline = game_datetime - timedelta(days=1)

    if kyiv_now > unregister_deadline:
        await callback.answer("⛔ Відписатися можна лише до 21:00 за день до гри.", show_alert=True)
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