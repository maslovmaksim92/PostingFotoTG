from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Глобальные настройки проекта"""

    telegram_bot_token: str = Field(alias="TG_GITHUB_BOT")
    telegram_chat_id: str = Field(alias="TG_CHAT_ID")
    openai_api_key: str
    bitrix_deal_update_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True
    )


settings = Settings()