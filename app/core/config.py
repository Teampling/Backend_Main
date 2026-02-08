from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    # APP
    app_env: str = "dev"
    app_name: str = "teampling-api"

    # DATABASE (compose에도 쓰는 값들)
    postgres_db: str
    postgres_user: str
    postgres_password: str
    database_url: str

    # JWT / AUTH
    jwt_secret: str
    jwt_alg: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 14

    # SECURITY
    password_hash_rounds: int = 12

    # CORS
    cors_origins: str = ""

    # LOGGING
    log_level: str = "INFO"

settings = Settings()
