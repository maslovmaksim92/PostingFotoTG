from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    OPENAI_API_KEY: str
    TG_CHAT_ID: str
    TG_GITHUB_BOT: str

    BASIC_AUTH_LOGIN: str
    BASIC_AUTH_PASSWORD: str

    FILE_FIELD_ID: str
    BITRIX_WEBHOOK: str


settings = Settings()