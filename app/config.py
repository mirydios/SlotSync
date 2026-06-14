from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://slotsync:slotsync_secret@localhost:5450/slotsync"

    # Auth
    SECRET_KEY: str = "supersecretkey_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # App
    APP_BASE_URL: str = "http://localhost:8010"

    # Email
    MAIL_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_NAME: str = "SlotSync"
    EMAILS_FROM_EMAIL: str = "noreply@slotsync.app"

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
