from flask import Flask, render_template, request, redirect, url_for, flash
from models.user import User
from models.game import Game
from models.registration import Registration
from models.payment import Payment
import os
from flask import session

from dotenv import load_dotenv
from aiogram import Bot
from aiogram.types import FSInputFile
from werkzeug.utils import secure_filename
import asyncio
from database import SessionLocal
import threading
from config import BOT_TOKEN
load_dotenv()
bot = Bot(token=BOT_TOKEN)

app = Flask(__name__)
app.secret_key = "your_secret_here"
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/users")
def list_users():
    users = User.all()
    return render_template("users.html", users=users)

@app.route("/user/<int:user_id>")
def user_profile(user_id):
    user = User.get(user_id)
    if not user:
        return "Користувача не знайдено", 404
    payments = Payment.get_user_payments(user_id)
    return render_template("user_profile.html", user=user, payments=payments)

@app.route("/update_status/<int:user_id>", methods=["POST"])
def update_status(user_id):
    new_status = request.form.get("status")
    User.update_status(user_id, new_status)
    flash("Статус оновлено!")
    return redirect(url_for("user_profile", user_id=user_id))

@app.route("/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    User.delete(user_id)
    return redirect(url_for("list_users"))

@app.route("/events")
def list_events():
    events = Game.all_upcoming()
    return render_template("events.html", events=[
        (
            e.id, e.date, e.time, e.location, e.type, e.host,
            Game.players_count(e.id),
            e.player_limit,
            e.media
        ) for e in events
    ])

async def send_announcement_to_users(users, event_text, markup, media_url):
    for user in users:
        tg_id = user.tg_id
        if not user.receive_notifications:
            continue
        try:
            if media_url:
                full_path = os.path.join("static", media_url)
                if media_url.endswith(".jpg") or media_url.endswith(".png") or media_url.endswith(".jpeg"):
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


def run_async_task(users, event_text, markup, media_url):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(send_announcement_to_users(users, event_text, markup, media_url))
    loop.close()

@app.route("/create_event", methods=["GET", "POST"])
def create_event():
    if request.method == "POST":
        data = dict(request.form)
        file = request.files.get("media")
        filename = ""
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            filename = f"uploads/{filename}"
        data["media_url"] = filename
        session["pending_event"] = data
        return redirect("/preview_event")

    return render_template("create_event.html")


@app.route("/preview_event", methods=["GET", "POST"])
def preview_event():
    data = session.get("pending_event")
    if not data:
        return redirect("/create_event")

    if request.method == "POST":
        game = Game.add(
            data["date"], data["time"], data["location"], data["type"],
            data["host"], data["media_url"], data["price"],
            data["player_limit"], data["description"]
        )
        game_id = game.id
        session.pop("pending_event", None)

        # Повідомлення
        event_text = f"📢 <b>Нова гра!</b>\n\n" \
                     f"📅 {data['date']} о {data['time']}\n📍 {data['location']}\n🎮 {data['type']}\n👤 Ведучий: {data['host'] or 'Невідомо'}"

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📥 Записатись", callback_data=f"signup:{game_id}"),
                    InlineKeyboardButton(text="👥 Переглянути гравців", callback_data=f"players:{game_id}")
                ]
            ]
        )

        users = User.all()
        threading.Thread(target=run_async_task, args=(users, event_text, markup, data["media_url"])).start()

        flash("Подію створено!")
        return redirect("/events")

    return render_template("preview_event.html", event=data)


@app.route("/event/<int:event_id>/players")
def show_registered_players(event_id):
    event = Game.get(event_id)
    if not event:
        return "Подію не знайдено", 404

    session = SessionLocal()
    regs = (
        session.query(Registration)
        .filter_by(game_id=event_id)
        .join(User, Registration.user_id == User.id)
        .with_entities(User.full_name, User.username)
        .all()
    )
    session.close()

    return render_template("registered_players.html", event=event, players=regs)


@app.route("/event/<int:event_id>", methods=["GET", "POST"])
def view_event(event_id):
    event = Game.get(event_id)
    if not event:
        return "Подію не знайдено", 404
    if request.method == "POST":
        date = request.form["date"]
        time = request.form["time"]
        location = request.form["location"]
        type_ = request.form["type"]
        host = request.form["host"]
        price = request.form["price"]
        player_limit = request.form["player_limit"]
        description = request.form["description"]
        file = request.files.get("media")
        media = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            media = f"uploads/{filename}"
        Game.update(event_id, date, time, location, type_, host, price, player_limit, description, media)
        return redirect(url_for("view_event", event_id=event_id))
    return render_template("view_event.html", event=event)

@app.route("/delete_event/<int:event_id>", methods=["POST"])
def delete_event(event_id):
    print(f"Deleting event with ID: {event_id}")
    Game.delete(event_id)
    return redirect(url_for("list_events"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8537)
