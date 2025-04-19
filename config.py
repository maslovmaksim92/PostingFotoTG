from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


settings = Settings()
