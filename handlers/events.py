from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold, hitalic
from handlers.start import get_back_to_main_menu
from database import SessionLocal
from models.user import User
from models.game import Game
from models.registration import Registration
from models.payment import Payment
from datetime import date
from wayforpay_client import WayForPayClient
from utils import safe_edit_or_send

router = Router()
wfp = WayForPayClient()

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

    
    message_ids = []
    for idx, game in enumerate(games):
        reg_count = session.query(Registration).filter(Registration.game_id == game.id).count()
        is_registered = session.query(Registration).filter_by(game_id=game.id, user_id=user.id).first() is not None

        text = f"📅 {hbold(game.date)} о {hitalic(game.time)}\n🎮 {game.type}\n📍 {game.location}\n👥 Записано: {reg_count}/{game.player_limit}"

        buttons = []
        if not is_registered:
            buttons.append([InlineKeyboardButton(text="📥 Записатись", callback_data=f"signup:{game.date}_{game.time}")])
        else:
            buttons.append([InlineKeyboardButton(text="❌ Відмовитись", callback_data=f"unregister:{game.id}")])
        buttons.append([InlineKeyboardButton(text="👥 Переглянути гравців", callback_data=f"players:{game.id}")])


        if idx == len(games) - 1:
            to_delete = "_".join(f"{mid}" for mid in message_ids)
            back_callback = f"main_menu_{to_delete}"
            buttons.append([InlineKeyboardButton(text="⬅️ Повернутись у меню", callback_data=back_callback)])

        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        if(idx == 0):
            msg = await safe_edit_or_send(callback.message, text, reply_markup=markup, parse_mode="HTML")
            message_ids.append(msg.message_id)
        else:
            msg = await callback.message.answer(text, reply_markup=markup, parse_mode="HTML")
            message_ids.append(msg.message_id)


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

    # ✅ Спочатку згенеруй order_reference
    order_reference = f"inv_{user.id}_{game.id}_{date_}_{int(time.replace(':',''))}"

    # 🔍 Перевірка наявності платежу
    existing_order = session.query(Payment).filter_by(order_reference=order_reference).first()

    if existing_order:
        if existing_order.status == "approved":
            already_registered = session.query(Registration).filter_by(user_id=user.id, game_id=game.id).first()
            if not already_registered:
                registration = Registration(user_id=user.id, game_id=game.id)
                session.add(registration)
                session.commit()
                await callback.message.answer("✅ Ви вже оплатили і вас зареєстровано на гру!")
            else:
                await callback.message.answer("✅ Ви вже зареєстровані на цю гру.")
            await callback.answer()
            session.close()
            return
        else:
            # redirect to payment (existing)
            buttons = [
                [InlineKeyboardButton(text=f"💳 Оплатити {existing_order.amount} грн", callback_data="pay_dummy")],
                [InlineKeyboardButton(text="🔁 Перевірити статус", callback_data=f"check_payment:{existing_order.order_reference}")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
            ]
            await callback.message.answer("💸 Оплата вже очікується. Перевірте статус або оплатіть повторно.", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
            await callback.answer()
            session.close()
            return

    # 🧮 Перевірка ліміту
    reg_count = session.query(Registration).filter_by(game_id=game.id).count()
    if game.player_limit and reg_count >= game.player_limit:
        await callback.answer("❌ Місць більше немає.", show_alert=True)
        session.close()
        return

    # 🧾 Генерація інвойсу
    amount = game.price or 0
    invoice = wfp.create_invoice(order_reference=order_reference, amount=amount, product_name="Game Registration")

    # 💾 Збереження платежу
    payment = Payment(
        user_id=user.id,
        game_id=game.id,
        amount=amount,
        payment_type="card",
        status="pending",
        order_reference=order_reference
    )
    session.add(payment)
    session.commit()

    # 🔘 Кнопки для оплати
    invoice_url = invoice.get("invoiceUrl")
    buttons = [
        [InlineKeyboardButton(text="💳 Перейти до оплати", url=invoice_url)],
        [InlineKeyboardButton(text="🔁 Перевірити статус", callback_data=f"check_payment:{order_reference}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ]

    await callback.message.answer("💸 Залишилось оплатити гру!", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()
    session.close()




@router.callback_query(lambda c: c.data.startswith("check_payment:"))
async def check_payment_status(callback: types.CallbackQuery):
    order_reference = callback.data.split("check_payment:")[1]
    print(order_reference)
    from wayforpay_client import WayForPayClient  # або інший твій шлях
    wfp = WayForPayClient()

    result = wfp.check_payment_status(order_reference)
    print(result)
    status = result.get("transactionStatus")

    if status == "Approved":
        session = SessionLocal()
        Payment.update_status_by_reference(order_reference, "paid")

        payment = session.query(Payment).filter_by(order_reference=order_reference).first()
        user = session.query(User).get(payment.user_id)
        game = session.query(Game).get(payment.game_id)

        already_registered = session.query(Registration).filter_by(user_id=user.id, game_id=game.id).first()
        if not already_registered:
            registration = Registration(user_id=user.id, game_id=game.id, payment_type="card")
            session.add(registration)
            session.commit()

        session.close()
        await callback.message.answer("✅ Оплату підтверджено! Ви зареєстровані на гру.")
    elif status == "Pending":
        await callback.answer("⏳ Оплата ще очікується...", show_alert=True)
    else:
        await callback.answer(f"❌ Статус оплати: {status}", show_alert=True)

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

    registration = session.query(Registration).filter_by(user_id=user.id, game_id=game_id).first()
    if registration:
        session.delete(registration)
        session.commit()
        await callback.answer("❌ Ви скасували свою участь.")
        await callback.message.answer("Ваша реєстрація скасована.")
    else:
        await callback.answer("⚠️ Ви не були записані на цю гру.", show_alert=True)
    session.close()
