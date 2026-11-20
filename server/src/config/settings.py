from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    REDIS_URL: str
    BASE_URL: str
    MAILTRAP_TOKEN: str
    MAIL_SENDER_NAME: str
    MAIL_SENDER_EMAIL: str
    FRONTEND_URL: str
    OAUTH_CLIENT_ID: str = ""
    APP_MODE: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


Config = Settings()
