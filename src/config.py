from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_SCRIPT_URL: str
    YANDEX_API_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env",  
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()