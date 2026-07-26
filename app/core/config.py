from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str | None = None
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Demo mode provisions a throwaway user and JWT on request so a public
    # deployment can be explored without registering. It never relaxes token
    # validation -- see app/services/demo_service.py.
    DEMO_MODE: bool = False
    DEMO_SESSION_EXPIRE_MINUTES: int = 720
    DEMO_MAX_SESSIONS_PER_HOUR: int = 60

    # Per-client ceiling, keyed by request.client.host. Behind a reverse proxy,
    # run uvicorn with --proxy-headers --forwarded-allow-ips=<proxy ip> or every
    # visitor shares the proxy address and this degrades into a second global
    # ceiling.
    DEMO_MAX_SESSIONS_PER_CLIENT_PER_HOUR: int = 5

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
