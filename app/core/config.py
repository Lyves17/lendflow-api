from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "LendFlow"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    MONGO_URL: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "lendflow"

    SECRET_KEY: str = "change-me-in-production-please"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    SENDGRID_API_KEY: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
