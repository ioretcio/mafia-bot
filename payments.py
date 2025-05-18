import hashlib
import base64
import hmac
import time
from flask import Blueprint, request, jsonify
from database import SessionLocal
from models import Payment, User, Game
import os

payments_bp = Blueprint("payments", __name__)

MERCHANT_ACCOUNT = os.getenv("merchantAccount")
MERCHANT_SECRET_KEY = os.getenv("merchantSecretKey")


# Хелпер для підпису
def generate_signature(params: dict, secret: str) -> str:
    keys = [
        "merchantAccount",
        "orderReference",
        "amount",
        "currency",
        "productName",
        "productCount",
        "productPrice"
    ]
    data = ";".join(str(params[k]) for k in keys)
    return base64.b64encode(hmac.new(secret.encode(), data.encode(), hashlib.md5).digest()).decode()


@payments_bp.route("/create_payment", methods=["POST"])
def create_payment():
    data = request.json
    user_id = data.get("user_id")
    game_id = data.get("game_id")
    amount = data.get("amount")

    session = SessionLocal()
    user = session.query(User).get(user_id)
    game = session.query(Game).get(game_id)

    if not user or not game:
        session.close()
        return jsonify({"error": "Invalid user or game"}), 400

    order_ref = f"ORDER-{user_id}-{game_id}-{int(time.time())}"

    payload = {
        "merchantAccount": MERCHANT_ACCOUNT,
        "orderReference": order_ref,
        "amount": amount,
        "currency": "UAH",
        "productName": [f"Гра {game.date} {game.time}"],
        "productCount": [1],
        "productPrice": [amount],
    }
    signature = generate_signature(payload, MERCHANT_SECRET_KEY)

    session.close()
    return jsonify({
        "url": "https://secure.wayforpay.com/pay",
        "data": {
            **payload,
            "merchantSignature": signature,
            "returnUrl": "https://your-site.com/payment_return",
            "serviceUrl": "https://your-site.com/payment_callback"
        }
    })


@payments_bp.route("/payment_callback", methods=["POST"])
def payment_callback():
    data = request.json
    if data.get("transactionStatus") == "Approved":
        session = SessionLocal()

        user_id = int(data.get("orderReference").split("-")[1])
        game_id = int(data.get("orderReference").split("-")[2])

        payment = Payment(
            user_id=user_id,
            game_id=game_id,
            amount=data.get("amount", 0),
            payment_type=data.get("paymentMethod", "online"),
            date=data.get("createdDate", time.strftime("%Y-%m-%d")),
            comment="WayForPay"
        )
        session.add(payment)
        session.commit()
        session.close()

    return jsonify({"status": "received"})