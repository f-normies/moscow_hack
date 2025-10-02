from celery import Celery
from app.config import settings

celery_app = Celery(
    "inference_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.INFERENCE_TIMEOUT,
    task_soft_time_limit=settings.INFERENCE_TIMEOUT - 60,
    worker_prefetch_multiplier=1,  # One task at a time for GPU
    worker_max_tasks_per_child=10,  # Restart worker to prevent memory leaks
)

if __name__ == "__main__":
    celery_app.start()
