"""
This module contains all Celery tasks for the application.
Tasks are organized in separate modules for better maintainability.
"""

# Import all tasks here for explicit registration if needed
from .campaign import celery_run_company_campaign

__all__ = ['celery_run_company_campaign'] 