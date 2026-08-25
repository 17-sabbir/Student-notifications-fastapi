from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote_plus


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DB_USER: str = "user"
    DB_PASSWORD: str = "password"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "student_notifications"
    DB_URL: str | None = None

    FIREBASE_CREDENTIALS_PATH: str = "firebase-service-account.json"
    FIREBASE_PROJECT_ID: str = "notifications-app-b29a7"

    CORS_ORIGINS: str
    RATE_LIMIT_AUTH: str = "5/minute"
    RATE_LIMIT_OTP: str = "5/15minutes"
    RATE_LIMIT_RESEND: str = "1/minute"


    @property
    def database_url(self) -> str:
        if self.DB_URL:
            return self.DB_URL
        password = quote_plus(self.DB_PASSWORD)
        return f"postgresql+asyncpg://{self.DB_USER}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
