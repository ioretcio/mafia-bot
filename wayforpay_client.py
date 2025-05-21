import hashlib
import hmac
import os
import time
import requests
import json
from dotenv import load_dotenv

load_dotenv()

MERCHANT_ACCOUNT = os.getenv("merchantAccount")
MERCHANT_SECRET_KEY = os.getenv("merchantSecretKey")
MERCHANT_DOMAIN = "test.wayforpay.com"


class WayForPayClient:
    def __init__(self):
        self.account = MERCHANT_ACCOUNT
        self.secret_key = MERCHANT_SECRET_KEY
        self.domain = MERCHANT_DOMAIN
        self.api_url = "https://api.wayforpay.com/api"

    def _generate_signature(self, data: list) -> str:
        sign_str = ";".join(map(str, data))
        return hmac.new(self.secret_key.encode(), sign_str.encode(), hashlib.md5).hexdigest()

    def create_invoice(self, order_reference: str, amount: float, product_name: str) -> dict:
        order_date = int(time.time())
        product_price = str(amount)
        product_count = "1"

        sign_parts = [
            self.account,
            self.domain,
            order_reference,
            str(order_date),
            str(amount),
            "UAH",
            product_name,
            product_count,
            product_price
        ]
        signature = self._generate_signature(sign_parts)

        payload = {
            "transactionType": "CREATE_INVOICE",
            "merchantAccount": self.account,
            "merchantAuthType": "SimpleSignature",
            "merchantDomainName": self.domain,
            "merchantSignature": signature,
            "apiVersion": 1,
            "language": "ua",
            "serviceUrl": "http://example.com/callback",
            "orderReference": order_reference,
            "orderDate": order_date,
            "amount": str(amount),
            "currency": "UAH",
            "orderTimeout": 86400,
            "productName": [product_name],
            "productPrice": [float(product_price)],
            "productCount": [int(product_count)]
        }

        response = requests.post(self.api_url, json=payload)
        return response.json()

    def check_payment_status(self, order_reference: str) -> dict:
        sign_parts = [
            self.account,
            order_reference
        ]
        signature = self._generate_signature(sign_parts)

        payload = {
            "transactionType": "CHECK_STATUS",
            "merchantAccount": self.account,
            "merchantAuthType": "SimpleSignature",
            "merchantDomainName": self.domain,
            "merchantSignature": signature,
            "apiVersion": 1,
            "orderReference": order_reference
        }

        response = requests.post(self.api_url, json=payload)
        return response.json()
