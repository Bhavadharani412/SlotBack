from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SlotBack API"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = ""
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

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            v_clean = v.strip()
            if not v_clean:
                return v_clean
            try:
                from urllib.parse import urlsplit, urlunsplit

                parsed = urlsplit(v_clean)
                if parsed.scheme in (
                    "postgres",
                    "postgresql",
                    "postgresql+psycopg",
                    "postgresql+psycopg2",
                    "postgresql+psycopg3",
                ):
                    return urlunsplit(parsed._replace(scheme="postgresql+psycopg"))
            except Exception:
                pass
            if v_clean.startswith("postgres://"):
                return "postgresql+psycopg://" + v_clean[len("postgres://") :]
            if v_clean.startswith("postgresql://") and not v_clean.startswith("postgresql+psycopg://"):
                return "postgresql+psycopg://" + v_clean[len("postgresql://") :]
        return v

    def validate_production_configuration(self) -> None:
        """Enforce strict security guards when running in production environment."""
        if self.app_env.lower() == "production":
            from urllib.parse import urlsplit

            # Enforce non-empty DATABASE_URL
            if not self.database_url or not self.database_url.strip():
                raise ValueError(
                    "CRITICAL PRODUCTION CONFIGURATION ERROR: DATABASE_URL environment variable is missing or empty. "
                    "A valid remote PostgreSQL connection string is required in production."
                )

            # Enforce remote database in production (fail fast on localhost)
            parsed_db = urlsplit(self.database_url.strip())
            hostname = (parsed_db.hostname or "").lower()
            if not hostname:
                raise ValueError(
                    "CRITICAL PRODUCTION CONFIGURATION ERROR: DATABASE_URL must include a valid remote database host."
                )
            if (
                hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1")
                or hostname.startswith("127.")
            ):
                raise ValueError(
                    f"CRITICAL PRODUCTION CONFIGURATION ERROR: DATABASE_URL points to localhost ('{hostname}'). "
                    "Production environment must use a remote managed database (e.g. Render PostgreSQL)."
                )

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
