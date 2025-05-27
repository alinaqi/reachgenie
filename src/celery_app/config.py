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
    task_time_limit=57600,  # 16 hour timeout
    task_soft_time_limit=57540,  # 15 hours and 59 minutes soft timeout
    worker_prefetch_multiplier=1,  # Process one task at a time
    task_acks_late=True,  # Tasks are acknowledged after completion
    
    # Redis key prefix settings
    redis_backend_use_ssl=False,  # Set to True if using SSL
    task_default_queue='reachgenie:normal',  # Default queue for tasks. We have added prefix "reachgenie:" because the queue_name_prefix setting is not working
    visibility_timeout=57600,  # Match task_time_limit (16 hours)
    broker_transport_options={
        'queue_name_prefix': 'reachgenie:',  # Prefix for all Redis queue keys
        'visibility_timeout': 57600  # Match task_time_limit (16 hours)
    },
    result_backend_transport_options={
        'global_keyprefix': 'reachgenie:',  # Prefix for result backend keys
        'visibility_timeout': 57600  # Match task_time_limit (16 hours)
    }
) 