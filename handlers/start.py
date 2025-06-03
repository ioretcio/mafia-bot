from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User
from utils import safe_edit_or_send
from aiogram import F
from database import SessionLocal
from wayforpay_client import WayForPayClient
from models.payment import Payment
from asyncio import create_task
router = Router()

wfp = WayForPayClient()
def get_back_to_main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Головне меню", callback_data="main_menu")]]
    )

async def check_user_pending_payments(user: User, bot, chat_id: int):
    session = SessionLocal()

    # try:
    pending_payments = session.query(Payment).filter_by(user_id=user.id, status="pending").all()
    print(f"Found {len(pending_payments)} pending payments for user {user.id}")
    for p in pending_payments:
        result = wfp.check_payment_status(p.order_reference)
        status = result.get("transactionStatus")
        print(f"Payment {p.id} status: {status}")
        if status == "Approved":
            user.balance += p.amount
            p.status = "paid"
            session.commit()
            await bot.send_message(chat_id, f"✅ Отримано оплату {p.amount} грн! Баланс поповнено.")
    # finally:
    #     session.close()



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
async def start_handler(message: types.Message):

    create_task(check_user_pending_payments(message.from_user, message.bot, message.chat.id))

    User.get_or_create(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name
    )
    await message.answer(
        f"👋 Привіт, {message.from_user.full_name}!",
        reply_markup=get_main_inline_menu()
    )