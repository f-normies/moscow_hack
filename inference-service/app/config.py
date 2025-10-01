from pydantic_settings import BaseSettings
from typing import List


class InferenceSettings(BaseSettings):
    model_config = {"env_file": "../.env", "env_ignore_empty": True, "extra": "ignore"}

    # Redis/Celery
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Database
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # MinIO
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool = False
    MINIO_BUCKET_NAME: str

    # Inference
    MODELS_PATH: str = "/models"
    ONNX_PROVIDERS: List[str] = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    GPU_MEMORY_LIMIT: int = 8 * 1024 * 1024 * 1024  # 8GB
    INFERENCE_TIMEOUT: int = 3600  # 1 hour

    # Processing
    MAX_WORKERS: int = 1  # GPU workers
    SLIDING_WINDOW_OVERLAP: float = 0.5
    USE_GAUSSIAN_WEIGHTING: bool = True
    USE_TEST_TIME_AUGMENTATION: bool = False
    BATCH_SIZE: int = 1


settings = InferenceSettings()  # type: ignore
