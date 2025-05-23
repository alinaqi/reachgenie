"""
This module contains all Celery tasks for the application.
Tasks are automatically discovered from separate modules in this directory.
No manual task registration is needed - just add new task files to this directory
and Celery will automatically find and register them.
"""

from ..config import celery_app as celery  # This is required for Celery to find the application