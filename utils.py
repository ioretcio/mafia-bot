from aiogram.types import Message


async def safe_edit_or_send(message: Message, text: str, reply_markup=None, parse_mode="HTML"):
    ret = None
    try:
        if message.text:  # якщо є текст, редагуємо
            ret = await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
            await message.delete()  # видаляємо оригінальне повідомлення, якщо редагування не вдалося
    except Exception as e:
        print(f"❌ safe_edit_or_send error: {e}")
        await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        await message.delete()  # видаляємо оригінальне повідомлення, якщо редагування не вдалося
    return ret