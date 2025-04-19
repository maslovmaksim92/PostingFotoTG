from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BITRIX_WEBHOOK: str
    BITRIX_TG_WEBHOOK_ISHOD: str
    OPENAI_API_KEY: str
    TG_CHAT_ID: str
    TG_GITHUB_BOT: str
    FILE_FIELD_ID: str
    FOLDER_FIELD_ID: str
    BITRIX_CLIENT_ID: str
    BITRIX_CLIENT_SECRET: str
    BITRIX_REDIRECT_URI: str
    BASIC_AUTH_LOGIN: str
    BASIC_AUTH_PASSWORD: str
    PORT: int = 10000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()