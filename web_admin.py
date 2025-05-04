from flask import Flask, render_template, request, redirect, url_for, flash
from db import get_connection
import os
from dotenv import load_dotenv
from aiogram import Bot
from aiogram.types import FSInputFile

from config import BOT_TOKEN
load_dotenv()
bot = Bot(token=BOT_TOKEN)
import asyncio


app = Flask(__name__)
app.secret_key = "your_secret_here"  # потрібен для flash-повідомлень

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/users")
def list_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return render_template("users.html", users=users)

# --- Події ---
@app.route("/events")
def list_events():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM games WHERE date >= DATE('now') ORDER BY date")
    events = c.fetchall()
    conn.close()
    return render_template("events.html", events=events)


from aiogram.types import FSInputFile

async def send_announcement_to_users(users, event_text, markup, media_url):
    for user in users:
        tg_id = user[0]
        try:
            if media_url:
                full_path = os.path.join("static", media_url)
                if media_url.endswith(".jpg") or media_url.endswith(".png"):
                    photo = FSInputFile(full_path)
                    await bot.send_photo(tg_id, photo=photo, caption=event_text, parse_mode="HTML", reply_markup=markup)
                elif media_url.endswith(".mp4"):
                    video = FSInputFile(full_path)
                    await bot.send_video(tg_id, video=video, caption=event_text, parse_mode="HTML", reply_markup=markup)
                else:
                    await bot.send_message(tg_id, text=event_text + f"\n\n📎 [Медіа]({media_url})", parse_mode="HTML", reply_markup=markup)
            else:
                await bot.send_message(tg_id, text=event_text, parse_mode="HTML", reply_markup=markup)
        except Exception as e:
            print(f"❌ Не вдалося надіслати повідомлення {tg_id}: {e}")



@app.route("/create_event", methods=["GET", "POST"])
def create_event():
    if request.method == "POST":
        date = request.form["date"]
        time = request.form["time"]
        location = request.form["location"]
        type_ = request.form["type"]
        host = request.form["host"]
        price = request.form["price"]
        file = request.files.get("media")
        conn = get_connection()
        c = conn.cursor()
        media_url = ""
        if file:
            filename = file.filename
            media_url = os.path.join("uploads", filename)  # зберігаємо як відносний шлях
            file.save(os.path.join(UPLOAD_FOLDER, filename))

        # Додай колонку media до INSERT
        c.execute('''
            INSERT INTO games (date, time, location, type, host, media, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (date, time, location, type_, host, media_url, price))
        conn.commit()

        

                # Розсилка всім користувачам
        c.execute("SELECT tg_id FROM users")
        users = c.fetchall()

        event_text = f"📢 <b>Нова гра!</b>\n\n" \
                     f"📅 {date} о {time}\n📍 {location}\n🎮 {type_}\n👤 Ведучий: {host or 'Невідомо'}"

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📥 Записатись", callback_data=f"signup:{date}_{time}")]
            ]
        )
        conn.close()
        print(event_text)
        asyncio.run(send_announcement_to_users(users, event_text, markup, media_url))
        return redirect(url_for("list_events"))

    return render_template("create_event.html")

@app.route("/event/<int:event_id>", methods=["GET", "POST"])
def view_event(event_id):
        conn = get_connection()
        c = conn.cursor()

        if request.method == "POST":
            date = request.form["date"]
            time = request.form["time"]
            location = request.form["location"]
            type_ = request.form["type"]
            host = request.form["host"]
            price = request.form["price"]
            c.execute('''
                UPDATE games
                SET date = ?, time = ?, location = ?, type = ?, host = ?, price = ?
                WHERE id = ?
            ''', (date, time, location, type_, host, price, event_id))
            conn.commit()

        c.execute("SELECT * FROM games WHERE id = ?", (event_id,))
        event = c.fetchone()
        conn.close()

        if not event:
            return "Подію не знайдено", 404

        return render_template("view_event.html", event=event)

@app.route("/delete_event/<int:event_id>", methods=["POST"])
def delete_event(event_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM games WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("list_events"))
if __name__ == "__main__":
    app.run(port=7654, debug=True)