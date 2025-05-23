from .config import celery_app

# Configure Celery to autodiscover tasks
celery_app.autodiscover_tasks(['src.celery_app.tasks'])

__all__ = ['celery_app'] 