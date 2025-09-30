"""
This module contains all Celery tasks for the application.
Each task should be imported and registered here.
"""

from ..config import celery_app as celery
from .run_campaign import celery_run_company_campaign
from .process_leads import celery_process_leads
from .process_do_not_contact import celery_process_do_not_contact

__all__ = ['celery', 'celery_run_company_campaign', 'celery_process_leads', 'celery_process_do_not_contact']