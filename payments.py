import hashlib
import base64
import hmac
import time
# from flask import Blueprint, request, jsonify
# from database import SessionLocal
# from models import Payment, User, Game
import os
from dotenv import load_dotenv
load_dotenv()
# payments_bp = Blueprint("payments", __name__)

MERCHANT_ACCOUNT = os.getenv("merchantAccount")
MERCHANT_SECRET_KEY = os.getenv("merchantSecretKey")

import hmac
import hashlib
import requests
import json

# === Вхідні дані ===
merchant_domain = "test.wayforpay.com"
order_reference = "test-order-123456"
order_date = 1747720000  # будь-яке число (timestamp)
amount = "1488"
currency = "UAH"
product_name = "Test product"
product_count = "1"
product_price = "1488"

print(MERCHANT_ACCOUNT, MERCHANT_SECRET_KEY)


# === Створення підпису ===
sign_parts = [
    MERCHANT_ACCOUNT,
    merchant_domain,
    order_reference,
    str(order_date),
    amount,
    currency,
    product_name,
    product_count,
    product_price
]
sign_str = ";".join(sign_parts)
signature = hmac.new(MERCHANT_SECRET_KEY.encode(), sign_str.encode(), hashlib.md5).hexdigest()

print("🧾 sign_str:", sign_str)
print("🔐 signature:", signature)

# === Формування запиту ===
payload = {
    "transactionType": "CREATE_INVOICE",
    "merchantAccount": MERCHANT_ACCOUNT,
    "merchantAuthType": "SimpleSignature",
    "merchantDomainName": merchant_domain,
    "merchantSignature": signature,
    "apiVersion": 1,
    "language": "en",
    "serviceUrl": "http://example.com/callback",
    "orderReference": order_reference,
    "orderDate": order_date,
    "amount": amount,
    "currency": currency,
    "orderTimeout": 86400,
    "productName": [product_name],
    "productPrice": [float(product_price)],
    "productCount": [int(product_count)],
    "clientFirstName": "Test",
    "clientLastName": "User",
    "clientEmail": "test@example.com",
    "clientPhone": "380000000000"
}

# === Відправлення ===
print("📤 Відправляємо запит до WayForPay...")
response = requests.post("https://api.wayforpay.com/api", json=payload)
print("📥 Статус:", response.status_code)

try:
    print("📦 Відповідь:", json.dumps(response.json(), indent=2, ensure_ascii=False))
except:
    print("❌ Не вдалося розпарсити відповідь")
    print("Raw:", response.text)