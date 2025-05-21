from celery import Celery
from src.config import get_settings

settings = get_settings()

# Initialize Celery with Redis backend
celery_app = Celery(
    'reachgenie',
    broker=settings.redis_url if hasattr(settings, 'redis_url') else 'redis://localhost:6379/0',
    backend=settings.redis_url if hasattr(settings, 'redis_url') else 'redis://localhost:6379/0'
)

# Configure Celery settings
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour timeout
    task_soft_time_limit=3540,  # 59 minutes soft timeout
    worker_prefetch_multiplier=1,  # Process one task at a time
    task_acks_late=True,  # Tasks are acknowledged after completion
) 