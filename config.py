import os
from dotenv import load_dotenv

load_dotenv()

# Read admin IDs as an array from .env
admin_ids = os.getenv("ADMIN_IDS", "").split(",")
BOT_TOKEN = os.getenv("BOT_TOKEN")