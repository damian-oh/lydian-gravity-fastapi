from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str
    DEBUG: bool = False
    DATABASE_URL: str | None = None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
