from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from handlers.start import get_main_inline_menu
from database import SessionLocal
from models.user import User
from models.payment import Payment
from wayforpay_client import WayForPayClient
from PIL import Image
from io import BytesIO
from aiogram.filters import StateFilter
import os
from utils import safe_edit_or_send

router = Router()
wfp = WayForPayClient()

class EditStates(StatesGroup):
    awaiting_new_username = State()
    awaiting_topup_amount = State()

@router.callback_query(F.data == "profile")
async def handle_profile(callback: types.CallbackQuery):
    session = SessionLocal()
    user = session.query(User).filter_by(tg_id=callback.from_user.id).first()
    if not user:
        await callback.message.answer("⚠️ Користувача не знайдено.")
        session.close()
        return
    print(f"User {user.balance} balance, games played: {user.games_played}, bonus points: {user.bonus_points}")
    text = f"👤 <b>Профіль</b>\n\n" \
           f"Ім'я: {user.full_name}\n" \
           f"Нік: @{user.username}\n" \
           f"Статус: {user.status}\n" \
           f"Баланс: {user.balance}💸\n"\
           f"Ігор відвідано: {user.games_played}\n" \
           f"Бонуси: {user.bonus_points}"

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Змінити Ім'я", callback_data="edit_username")],
        [InlineKeyboardButton(text="💰 Поповнити баланс", callback_data="topup_balance")],
        [InlineKeyboardButton(text="🖼 Змінити фото", callback_data="edit_photo")],
        [InlineKeyboardButton(text="⬅️ Головне меню", callback_data="main_menu")]
    ])

    photo_path = os.path.join("static", user.photo) if user.photo else "static/defaults/anon.jpg"
    try:
        photo = FSInputFile(photo_path)
        await callback.message.answer_photo(photo=photo, caption=text, parse_mode="HTML", reply_markup=markup)
        try:
            await callback.message.delete()
        except Exception:
                pass
    except Exception as e:
        await callback.message.answer("⚠️ Не вдалося завантажити фото профілю.")
        print(f"❌ Помилка завантаження фото: {e}")
    await callback.answer()

@router.callback_query(F.data == "topup_balance")
async def prompt_topup_amount(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("💸 Введи суму, яку хочеш поповнити (в грн):")
    try:
        await callback.message.delete()
    except Exception:
        pass
    await state.set_state(EditStates.awaiting_topup_amount)

@router.message(F.text, StateFilter(EditStates.awaiting_topup_amount))
async def handle_topup_amount(message: types.Message, state: FSMContext):
    amount_str = message.text.strip()
    if not amount_str.replace('.', '', 1).isdigit():
        await message.answer("❗ Введи коректну суму (наприклад, 100 або 99.50)")
        return

    amount = int(amount_str)
    session = SessionLocal()
    user = session.query(User).filter_by(tg_id=message.from_user.id).first()
    if not user:
        await message.answer("⚠️ Користувача не знайдено.")
        session.close()
        return

    order_reference = f"topup_{user.id}_{int(amount * 100)}_{int(message.date.timestamp())}"
    invoice = wfp.create_invoice(order_reference=order_reference, amount=amount, product_name="Up")

    # Запис у Payment
    payment = Payment(
        user_id=user.id,
        game_id=None,
        amount=amount,
        payment_type="card",
        status="pending",
        order_reference=order_reference
    )
    session.add(payment)
    session.commit()
    session.close()

    invoice_url = invoice.get("invoiceUrl")
    if not invoice_url:
        await message.answer("❌ Не вдалося створити інвойс. Спробуй пізніше.")
        await state.clear()
        return

    buttons = [
        [InlineKeyboardButton(text="💳 Перейти до оплати", url=invoice_url)],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]
    ]

    await message.answer(f"🔁 Оплата {amount} грн — після підтвердження сума буде зарахована на твій баланс.", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.clear()

@router.callback_query(F.data == "edit_photo")
async def prompt_photo_upload(callback: types.CallbackQuery):
    await callback.message.answer("📤 Надішли нове фото профілю як окреме зображення.")
    try:
        await callback.message.delete()
    except Exception:
            pass
@router.message(F.photo)
async def handle_profile_photo(message: types.Message):
    session = SessionLocal()
    user = session.query(User).filter_by(tg_id=message.from_user.id).first()
    if not user:
        await message.answer("⚠️ Користувача не знайдено.")
        session.close()
        return

    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_bytes = await message.bot.download_file(file.file_path)

    try:
        image = Image.open(BytesIO(file_bytes.read()))
        w, h = image.size
        side = min(w, h)
        cropped = image.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
        resized = cropped.resize((1000, 1000))

        os.makedirs("static/profile_photos", exist_ok=True)
        save_path = f"static/profile_photos/{message.from_user.id}.jpg"
        resized.save(save_path)
        user.photo = f"profile_photos/{message.from_user.id}.jpg"
        session.commit()

        await message.answer("✅ Фото оновлено!")
        await safe_edit_or_send(message, f"👋 Продовжимо!", reply_markup=get_main_inline_menu())
    except Exception as e:
        await message.answer("❌ Не вдалося обробити фото.")
        print(f"Помилка обробки фото: {e}")
    finally:
        session.close()

@router.callback_query(F.data == "edit_username")
async def prompt_fullname(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("✍️ Надішли нове ім’я")
    try:
        await callback.message.delete()
    except Exception:
        pass
    await state.set_state(EditStates.awaiting_new_username)

@router.message(F.text, StateFilter(EditStates.awaiting_new_username))
async def save_new_fullname(message: types.Message, state: FSMContext):
    new_fullname = message.text.strip()
    session = SessionLocal()
    user = session.query(User).filter_by(tg_id=message.from_user.id).first()
    if not user:
        await message.answer("⚠️ Користувача не знайдено.")
        session.close()
        return

    user.full_name = new_fullname
    session.commit()
    session.close()
    await message.answer(f"✅ Ім’я оновлено на {new_fullname}")
    await safe_edit_or_send(message, f"👋 Продовжимо!", reply_markup=get_main_inline_menu())
    await state.clear()
