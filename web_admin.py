from flask import Flask, render_template, request, redirect, url_for
from db import get_connection

app = Flask(__name__)

@app.route("/")
def list_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return render_template("users.html", users=users)

@app.route("/user/<int:user_id>")
def user_profile(user_id):
    conn = get_connection()
    c = conn.cursor()

    # Інфо про користувача
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()

    # Історія оплат
    c.execute("SELECT date, amount, payment_type, comment FROM payments WHERE user_id = ? ORDER BY date DESC", (user_id,))
    payments = c.fetchall()

    conn.close()

    if not user:
        return "Користувача не знайдено", 404
    return render_template("user_profile.html", user=user, payments=payments)

@app.route("/update_status/<int:user_id>", methods=["POST"])
def update_status(user_id):
    new_status = request.form.get("status")
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET status = ? WHERE id = ?", (new_status, user_id))
    conn.commit()
    conn.close()
    return redirect(url_for("user_profile", user_id=user_id))

@app.route("/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("list_users"))


if __name__ == "__main__":
    app.run(port=7654, debug=True)