import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings
from django.apps import apps
import logging

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')

app = Celery('ecommerce')
app.config_from_object('django.conf:settings', namespace='CELERY')
# Load task modules from all registered Django apps.
app.config_from_object(settings)

logger = logging.getLogger('celery')

app.autodiscover_tasks(lambda: [n.name for n in apps.get_app_configs()])

app.conf.beat_schedule = {
    'check_and_notify_stock_levels': {
        'task': 'inventory.tasks.check_and_notify_stock_levels',
        'schedule': crontab(minute='*/10'),
    },
    
}
