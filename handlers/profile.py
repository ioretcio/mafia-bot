from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from handlers.start import get_back_to_main_menu,get_main_inline_menu
from database import SessionLocal
from models.user import User
from PIL import Image
from io import BytesIO
from aiogram.filters import StateFilter
import os
from utils import safe_edit_or_send

router = Router()

class EditStates(StatesGroup):
    awaiting_new_username = State()

@router.callback_query(F.data == "profile")
async def handle_profile(callback: types.CallbackQuery):
    user = User.get_by_tg_id(callback.from_user.id)
    if not user:
        await callback.message.answer("⚠️ Користувача не знайдено.")
        return

    text = f"👤 <b>Профіль</b>\n\n" \
           f"Ім'я: {user.full_name}\n" \
           f"Нік: @{user.username}\n" \
           f"Статус: {user.status}\n" \
           f"Ігор відвідано: {user.games_played}\n" \
           f"Бонуси: {user.bonus_points}"

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Змінити нік", callback_data="edit_username")],
        [InlineKeyboardButton(text="🖼 Змінити фото", callback_data="edit_photo")],
        [InlineKeyboardButton(text="⬅️ Головне меню", callback_data="main_menu")]
    ])

    photo_path = os.path.join("static", user.photo) if user.photo else "static/resources/anon_user.png"
    try:
        photo = FSInputFile(photo_path)
        await callback.message.answer_photo(photo=photo, caption=text, parse_mode="HTML", reply_markup=markup)
        await callback.message.delete()
    except Exception as e:
        await callback.message.answer("⚠️ Не вдалося завантажити фото профілю.")
        print(f"❌ Помилка завантаження фото: {e}")
    await callback.answer()


@router.callback_query(F.data == "edit_photo")
async def prompt_photo_upload(callback: types.CallbackQuery):
    await callback.message.answer("📤 Надішли нове фото профілю як окреме зображення.")
    await callback.message.delete()


@router.message(F.photo)
async def handle_profile_photo(message: types.Message):
    # ORM: оновлення photo через SQLAlchemy
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

        # Оновлюємо поле photo через ORM
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
async def prompt_username(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("✍️ Надішли новий нікнейм (без @)")
    await callback.message.delete()
    await state.set_state(EditStates.awaiting_new_username)


@router.message(F.text, StateFilter(EditStates.awaiting_new_username))
async def save_new_username(message: types.Message, state: FSMContext):
    new_username = message.text.strip().lstrip("@")
    session = SessionLocal()
    user = session.query(User).filter_by(tg_id=message.from_user.id).first()
    if not user:
        await message.answer("⚠️ Користувача не знайдено.")
        session.close()
        return

    user.username = new_username
    session.commit()
    session.close()
    await message.answer(f"✅ Нік оновлено на @{new_username}")
    await safe_edit_or_send(message, f"👋 Продовжимо!", reply_markup=get_main_inline_menu())
    await state.clear()
