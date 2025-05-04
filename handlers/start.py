from aiogram import Router, types
from aiogram.filters import Command
from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from models import User
from aiogram.types import FSInputFile
import os
from PIL import Image
from io import BytesIO
from db import get_connection

router = Router()


from aiogram.fsm.state import State, StatesGroup

class EditStates(StatesGroup):
    awaiting_new_username = State()
    awaiting_photo = State()


def get_back_to_main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Головне меню", callback_data="main_menu")]
        ]
    )

def get_main_inline_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Переглянути профіль", callback_data="profile")],
            [InlineKeyboardButton(text="📛 Замовити іменну табличку", callback_data="nameplate")],
            [InlineKeyboardButton(text="📊 Історія відвідувань і оплат", callback_data="history")],
            [InlineKeyboardButton(text="⚙️ Налаштування та сповіщення", callback_data="settings")],
            [InlineKeyboardButton(text="📅 Заплановані івенти", callback_data="upcoming_events")]  # ← нова кнопка
        ]
    )

async def safe_edit_or_send(message: Message, text: str, reply_markup=None, parse_mode="HTML"):
    try:
        if message.text:  # якщо є текст, редагуємо
            await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        print(f"❌ safe_edit_or_send error: {e}")
        await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
                             
# /start
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

# Обробка натискань
@router.callback_query(F.data == "profile")
async def handle_menu_callback(callback: types.CallbackQuery):
    action = callback.data

    if action == "profile":
        user = User.get_by_tg_id(callback.from_user.id)

        text = f"👤 <b>Профіль</b>\n\n" \
               f"Ім’я: {user[3]}\n" \
               f"Нік: @{user[2]}\n" \
               f"Статус: {user[5]}\n" \
               f"Ігор відвідано: {user[6]}\n" \
               f"Бонуси: {user[7]}"
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Змінити нік", callback_data="edit_username")],
            [InlineKeyboardButton(text="🖼 Змінити фото", callback_data="edit_photo")],
            [InlineKeyboardButton(text="⬅️ Головне меню", callback_data="main_menu")]
        ])
        # Шлях до фото
        if user[4]:  # поле photo не пусте
            photo_path = os.path.join("static", user[4])
        else:
            photo_path = "resources/anon_user.png"

        try:
            photo = FSInputFile(photo_path)
            await callback.message.answer_photo(photo=photo, caption=text, parse_mode="HTML", reply_markup=markup)
            await callback.message.delete()
        except Exception as e:
            await callback.message.answer("⚠️ Не вдалося завантажити фото профілю.")
            print(f"❌ Помилка завантаження фото: {e}")
    await callback.answer()

@router.callback_query(F.data == "nameplate")
async def handle_nameplate(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📛 Форма замовлення таблички буде тут.",
        reply_markup=get_back_to_main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "history")
async def handle_history(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📊 Тут буде історія ігор та оплат.",
        reply_markup=get_back_to_main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "settings")
async def handle_settings(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "⚙️ Тут будуть налаштування та сповіщення.",
        reply_markup=get_back_to_main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def handle_main_menu(callback: types.CallbackQuery):
    await safe_edit_or_send(callback.message, f"👋 Привіт, {callback.from_user.full_name}!", reply_markup=get_main_inline_menu())
    await callback.message.delete()


@router.callback_query(lambda c: c.data == "edit_photo")
async def prompt_photo_upload(callback: types.CallbackQuery):
    await callback.message.answer("📤 Надішли нове фото профілю як окреме зображення.")
    await callback.message.delete()


@router.callback_query(F.data == "upcoming_events")
async def show_upcoming_events(callback: types.CallbackQuery):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT date, time, location, type FROM games WHERE date >= DATE('now') ORDER BY date LIMIT 5")
    events = c.fetchall()
    conn.close()

    if not events:
        text = "🔕 Наразі немає запланованих подій."
    else:
        text = "📅 <b>Найближчі події:</b>\n\n"
        for e in events:
            date, time, location, type_ = e
            text += f"• <b>{date}</b> о <i>{time}</i> — {type_} ({location})\n"

    await callback.message.edit_text(text, reply_markup=get_back_to_main_menu(),parse_mode="HTML")

@router.message(F.photo)
async def handle_profile_photo(message: types.Message):
    user = User.get_by_tg_id(message.from_user.id)
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_bytes = await message.bot.download_file(file.file_path)

    try:
        image = Image.open(BytesIO(file_bytes.read()))
        w, h = image.size
        side = min(w, h)

        # Central crop
        left = (w - side) // 2
        top = (h - side) // 2
        cropped = image.crop((left, top, left + side, top + side))
        resized = cropped.resize((1000, 1000))

        # Save
        os.makedirs("static/profile_photos", exist_ok=True)
        save_path = f"static/profile_photos/{message.from_user.id}.jpg"
        resized.save(save_path)

        # Update DB
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET photo = ? WHERE tg_id = ?", (f"profile_photos/{message.from_user.id}.jpg", message.from_user.id))
        conn.commit()
        conn.close()

        await message.answer("✅ Фото оновлено!")
    except Exception as e:
        await message.answer("❌ Не вдалося обробити фото.")
        print(f"Помилка обробки фото: {e}")


@router.callback_query(lambda c: c.data == "edit_username")
async def prompt_username(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("✍️ Надішли новий нікнейм (без @)")
    await callback.message.delete()
    # Збережемо стан
    await state.set_state(EditStates.awaiting_new_username)


@router.message(F.text, StateFilter(EditStates.awaiting_new_username))
async def save_new_username(message: types.Message, state: FSMContext):
    new_username = message.text.strip().lstrip("@")
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET username = ? WHERE tg_id = ?", (new_username, message.from_user.id))
    conn.commit()
    conn.close()
    await message.answer(f"✅ Нік оновлено на @{new_username}")
    await state.clear()