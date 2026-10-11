from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SlotBack API"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str
    test_database_url: str = ""
    cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"

    # Security & Authentication
    secret_key: str = "slotback-insecure-dev-secret-key-change-in-production-min32chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    initial_admin_email: str = "admin@gmail.com"
    initial_admin_password: str = ""

    # Email / Notification Provider
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "notifications@slotback.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def validate_production_configuration(self) -> None:
        """Enforce strict security guards when running in production environment."""
        if self.app_env.lower() == "production":
            if (
                self.secret_key
                == "slotback-insecure-dev-secret-key-change-in-production-min32chars"
                or len(self.secret_key) < 32
            ):
                raise ValueError(
                    "CRITICAL PRODUCTION SECURITY ERROR: SECRET_KEY must be a unique, high-entropy string "
                    "with at least 32 characters in production."
                )
            if self.debug:
                raise ValueError(
                    "CRITICAL PRODUCTION SECURITY ERROR: DEBUG must be false in production."
                )
            origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
            if "*" in origins or not origins:
                raise ValueError(
                    "CRITICAL PRODUCTION SECURITY ERROR: Wildcard CORS ('*') or empty CORS_ORIGINS "
                    "is prohibited in production when credentials are enabled."
                )


settings = Settings()
