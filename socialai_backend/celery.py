"""
Celery configuration for scheduled post publishing
"""
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialai_backend.settings')

app = Celery('socialai_backend')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'publish-scheduled-posts': {
        'task': 'posts.tasks.publish_scheduled_posts',
        'schedule': 60.0,  # Run every 60 seconds (1 minute)
    },
}

app.conf.timezone = settings.TIME_ZONE

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

