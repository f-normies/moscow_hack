"""Celery client for connecting to inference workers"""

from celery import Celery
from app.core.config import settings

# Create Celery client instance for backend to communicate with inference workers
celery_app = Celery(
    "inference_client",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Configure Celery client
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)


def get_active_workers() -> int:
    """Get count of active inference workers"""
    try:
        inspector = celery_app.control.inspect()
        stats = inspector.stats()

        if stats is None:
            return 0

        return len(stats)
    except Exception:
        return 0
