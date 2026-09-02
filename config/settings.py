import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    WOOLIX_API_KEY: str = os.getenv("WOOLIX_API_KEY", "")
    DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")
    
    # NOWPayments Settings
    NOWPAYMENTS_API_KEY: str = os.getenv("NOWPAYMENTS_API_KEY", "")
    NOWPAYMENTS_CALLBACK_URL: str = os.getenv("NOWPAYMENTS_CALLBACK_URL", "http://localhost:8000/webhook/nowpayments")

    IMAP_HOST: str = os.getenv("IMAP_HOST", "imap.gmail.com")
    IMAP_USER: str = os.getenv("IMAP_USER", "")
    IMAP_PASS: str = os.getenv("IMAP_PASS", "")
    ZELLE_RECIPIENT_EMAIL: str = os.getenv("ZELLE_RECIPIENT_EMAIL", "")

settings = Settings()