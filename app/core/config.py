from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    # APP
    APP_ENV: str
    APP_NAME: str

    # DATABASE
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )

    @property
    def LOCAL_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@localhost:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )

    # JWT / AUTH
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 30
    REFRESH_TOKEN_DAYS: int = 14

    # SECURITY
    PASSWORD_HASH_ROUNDS: int = 12

    # CORS
    CORS_ORIGINS: str = ""

    # LOGGING
    LOG_LEVEL: str = "INFO"

    # Oracle Cloud Storage
    OCI_USER_OCID: str = ""
    OCI_API_KEY_PATH: str = ""
    OCI_FINGERPRINT: str = ""
    OCI_TENANCY_OCID: str = ""
    OCI_REGION: str = ""
    OCI_OBJECT_STORAGE_NAMESPACE: str = ""
    OCI_OBJECT_STORAGE_BUCKET: str = ""

settings = Settings()
