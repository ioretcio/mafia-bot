from aiogram.types import Message


async def safe_edit_or_send(message: Message, text: str, reply_markup=None, parse_mode="HTML"):
    try:
        if message.text:  # якщо є текст, редагуємо
            await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        print(f"❌ safe_edit_or_send error: {e}")
        await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)