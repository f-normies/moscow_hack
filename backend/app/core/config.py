import secrets
import warnings
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


def parse_file_types(v: Any) -> list[str]:
    """Parse comma-separated file types from environment variable."""
    if isinstance(v, str):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list):
        return v
    elif v is None:
        return []
    raise ValueError(f"Invalid file types format: {v}")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:5173"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: EmailStr | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str

    # MinIO Configuration
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool
    MINIO_BUCKET_NAME: str

    # File upload configuration - categorized file types
    ALLOWED_IMAGE_TYPES: str = ""
    ALLOWED_DOCUMENT_TYPES: str = ""
    ALLOWED_VIDEO_TYPES: str = ""
    ALLOWED_AUDIO_TYPES: str = ""
    ALLOWED_OTHER_TYPES: str = ""

    # File size limits per category (in bytes)
    MAX_IMAGE_SIZE: int = 10 * 1024 * 1024  # 10MB
    MAX_DOCUMENT_SIZE: int = 50 * 1024 * 1024  # 50MB
    MAX_VIDEO_SIZE: int = 200 * 1024 * 1024  # 200MB
    MAX_AUDIO_SIZE: int = 50 * 1024 * 1024  # 50MB
    MAX_OTHER_SIZE: int = 100 * 1024 * 1024  # 100MB

    # General file size limit (fallback/legacy)
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB

    # Inference service configuration
    REDIS_URL: str = "redis://redis:6379/0"
    INFERENCE_MODELS_PATH: str = "/models"
    INFERENCE_TIMEOUT: int = 3600  # 1 hour max
    ONNX_PROVIDERS: list[str] = ["CUDAExecutionProvider", "CPUExecutionProvider"]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ALLOWED_FILE_TYPES(self) -> list[str]:
        """Combined list of all allowed file types from all categories."""
        return (
            parse_file_types(self.ALLOWED_IMAGE_TYPES)
            + parse_file_types(self.ALLOWED_DOCUMENT_TYPES)
            + parse_file_types(self.ALLOWED_VIDEO_TYPES)
            + parse_file_types(self.ALLOWED_AUDIO_TYPES)
            + parse_file_types(self.ALLOWED_OTHER_TYPES)
        )

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )
        self._check_default_secret("MINIO_SECRET_KEY", self.MINIO_SECRET_KEY)

        return self


settings = Settings()  # type: ignore
