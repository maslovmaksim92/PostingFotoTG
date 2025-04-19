from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    OPENAI_API_KEY: str
    TG_CHAT_ID: str
    TG_GITHUB_BOT: str

    BASIC_AUTH_LOGIN: str
    BASIC_AUTH_PASSWORD: str

    BITRIX_CLIENT_ID: str
    BITRIX_CLIENT_SECRET: str

    FILE_FIELD_ID: str
    FOLDER_FIELD_ID: str


settings = Settings()