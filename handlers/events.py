from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db import get_connection
from handlers.start import get_back_to_main_menu
from models import User
router = Router()
from aiogram.utils.markdown import hbold, hitalic

@router.callback_query(F.data == "upcoming_events")
async def show_upcoming_events(callback: types.CallbackQuery):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT 
            g.id, g.date, g.time, g.location, g.type, 
            (SELECT COUNT(*) FROM registrations r WHERE r.game_id = g.id) as reg_count,
            g.player_limit
        FROM games g
        WHERE g.date >= DATE('now')
        ORDER BY g.date LIMIT 5
    """)
    events = c.fetchall()
    conn.close()

    if not events:
        await callback.message.edit_text("🔕 Наразі немає запланованих подій.", reply_markup=get_back_to_main_menu())
        await callback.answer()
        return

    await callback.message.delete()

    for event in events:
        game_id, date, time, location, type_, reg_count, player_limit = event
        text = f"📅 {hbold(date)} о {hitalic(time)}\n🎮 {type_}\n📍 {location}\n👥 Записано: {reg_count}/{player_limit}"
        buttons = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📥 Записатись", callback_data=f"signup:{date}_{time}")],
                [InlineKeyboardButton(text="👥 Переглянути гравців", callback_data=f"players:{game_id}")],
                [InlineKeyboardButton(text="❌ Відмовитись", callback_data=f"unregister:{game_id}")]
            ]
        )
        await callback.message.answer(text, reply_markup=buttons, parse_mode="HTML")

    await callback.message.answer("⬅️ Повернутись у меню", reply_markup=get_back_to_main_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("signup:"))
async def handle_signup(callback: types.CallbackQuery):
    data = callback.data.split("signup:")[1]
    date, time = data.split("_")

    conn = get_connection()
    c = conn.cursor()

    # Знаходимо гру по даті та часу
    c.execute("SELECT id FROM games WHERE date = ? AND time = ?", (date, time))
    game = c.fetchone()

    if not game:
        await callback.answer("⚠️ Гру не знайдено!", show_alert=True)
        conn.close()
        return

    game_id = game[0]

    # Отримуємо user.id за tg_id
    user = User.get_by_tg_id(callback.from_user.id)
    if not user:
        await callback.answer("⚠️ Користувача не знайдено!", show_alert=True)
        conn.close()
        return

    user_id = user[0]

    # Перевірка чи вже записаний
    c.execute("SELECT id FROM registrations WHERE user_id = ? AND game_id = ?", (user_id, game_id))
    existing = c.fetchone()
    if existing:
        await callback.answer("ℹ️ Ви вже записані на цю гру.", show_alert=True)
        conn.close()
        return

    # Перевірка на ліміт
    c.execute("SELECT COUNT(*) FROM registrations WHERE game_id = ?", (game_id,))
    reg_count = c.fetchone()[0]
    c.execute("SELECT player_limit FROM games WHERE id = ?", (game_id,))
    player_limit = c.fetchone()[0]
    if player_limit and reg_count >= player_limit:
        await callback.answer("❌ Місць більше немає.", show_alert=True)
        conn.close()
        return

    # Запис до таблиці registrations
    c.execute(
        "INSERT INTO registrations (user_id, game_id, payment_type, present) VALUES (?, ?, ?, ?)",
        (user_id, game_id, "pending", 1)
    )
    conn.commit()
    conn.close()

    await callback.answer("✅ Ви записані на гру!")


@router.callback_query(lambda c: c.data.startswith("players:"))
async def handle_show_players(callback: types.CallbackQuery):
    game_id = callback.data.split("players:")[1]

    conn = get_connection()
    c = conn.cursor()

    # Отримати зареєстрованих користувачів
    c.execute("""
        SELECT u.full_name, u.username
        FROM registrations r
        JOIN users u ON r.user_id = u.id
        WHERE r.game_id = ?
    """, (game_id,))
    players = c.fetchall()
    conn.close()

    if not players:
        text = "🔍 Поки що ніхто не записався."
    else:
        text = "👥 <b>Учасники гри:</b>\n\n"
        for i, (full_name, username) in enumerate(players, 1):
            text += f"{i}. {full_name}"
            if username:
                text += f" (@{username})"
            text += "\n"

    await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(lambda c: c.data.startswith("unregister:"))
async def handle_unregister(callback: types.CallbackQuery):
    game_id = callback.data.split("unregister:")[1]

    conn = get_connection()
    c = conn.cursor()

    # Отримати user_id по tg_id
    c.execute("SELECT id FROM users WHERE tg_id = ?", (callback.from_user.id,))
    row = c.fetchone()
    if not row:
        await callback.answer("⚠️ Вас не знайдено в базі.", show_alert=True)
        conn.close()
        return

    user_id = row[0]

    # Видалити запис на гру
    c.execute("DELETE FROM registrations WHERE user_id = ? AND game_id = ?", (user_id, game_id))
    conn.commit()
    conn.close()

    await callback.answer("❌ Ви скасували свою участь.")
    await callback.message.answer("Ваша реєстрація скасована.")