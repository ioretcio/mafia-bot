from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User
from utils.utils import safe_edit_or_send
from aiogram import F
from models.database import SessionLocal
from utils.wayforpay_client import WayForPayClient
from models.payment import Payment
from aiogram.filters import CommandObject

from asyncio import create_task
router = Router()

wfp = WayForPayClient()
def get_back_to_main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Головне меню", callback_data="main_menu")]]
    )

async def check_user_pending_payments(user: User, bot, chat_id: int):
    session = SessionLocal()

    # Отримати користувача заново з цього session
    db_user = session.query(User).filter_by(id=user.id).first()

    pending_payments = session.query(Payment).filter_by(user_id=db_user.id, status="pending").all()
    print(f"Found {len(pending_payments)} pending payments for user {db_user.id}")

    for p in pending_payments:
        result = wfp.check_payment_status(p.order_reference)
        status = result.get("transactionStatus")
        print(f"Payment {p.id} status: {status}")

        if status == "Approved":
            db_user.balance += p.amount
            p.status = "paid"
            session.commit()
            await bot.send_message(chat_id, f"✅ Отримано оплату {p.amount} грн! Баланс поповнено.")

        elif status == "Declined":
            p.status = "declined"
            session.commit()
            await bot.send_message(chat_id, f"❌ Оплата на {p.amount} грн була відхилена.")

    session.close()



@router.callback_query(F.data.startswith("main_menu"))
async def handle_main_menu(callback: types.CallbackQuery):
    session = SessionLocal()
    user = session.query(User).filter_by(tg_id=callback.from_user.id).first()
    if not user:
        await callback.message.answer("⚠️ Користувача не знайдено.")
        session.close()
        return
    parts = callback.data.split("_")[2:]  # все після main_menu_
    for part in parts:
        try:
            msg_id = int(part)
            await callback.bot.delete_message(callback.message.chat.id, msg_id)
        except Exception as e:
            print(f"❌ Не вдалося видалити {part}: {e}")


    create_task(check_user_pending_payments(user, callback.bot, callback.message.chat.id))


    
    # Редагуємо поточне
    await safe_edit_or_send(
        callback.message,
        f"👋 Привіт, {callback.from_user.full_name}!",
        reply_markup=get_main_inline_menu()
    )
    await callback.answer()



def get_main_inline_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Переглянути профіль", callback_data="profile")],
            # [InlineKeyboardButton(text="📛 Замовити іменну табличку", callback_data="nameplate")],
            # [InlineKeyboardButton(text="📊 Історія відвідувань і оплат", callback_data="history")],
            # [InlineKeyboardButton(text="⚙️ Налаштування та сповіщення", callback_data="settings")],
            [InlineKeyboardButton(text="📅 Заплановані івенти", callback_data="upcoming_events")]
        ]
    )


@router.message(Command("start"))
async def start_handler(message: types.Message, command: CommandObject):
    session = SessionLocal()
    tg_id = message.from_user.id
    user = session.query(User).filter_by(tg_id=tg_id).first()

    if user:
        # 👤 Зареєстрований — нормальна взаємодія
        create_task(check_user_pending_payments(user, message.bot, message.chat.id))
        await message.answer(f"👋 Привіт, {message.from_user.full_name}!", reply_markup=get_main_inline_menu())
        return

    # 🧪 Перевірка параметра
    if command.args == "alohomora":
        # 🔐 Магічне слово — зареєструвати
        new_user = User(
            tg_id=tg_id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            photo="",
            status="active",
            games_played=0,
            bonus_points=0,
            receive_notifications=True,
            balance=0
        )
        session.add(new_user)
        session.commit()
        await message.answer("✅ Вас успішно зареєстровано!", reply_markup=get_main_inline_menu())
        return

    # ❌ Без параметра і не зареєстрований
    await message.answer("❌ Схоже, не ваш день...")