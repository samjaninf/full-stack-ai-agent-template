{%- if cookiecutter.use_celery %}
"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings
{%- if cookiecutter.enable_logfire and cookiecutter.logfire_celery %}
from app.core.logfire_setup import instrument_celery
{%- endif %}

# Create Celery app
celery_app = Celery(
    "{{ cookiecutter.project_slug }}",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="{{ cookiecutter.timezone }}",
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Result settings
    result_expires=3600,  # 1 hour
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
)

# Autodiscover tasks from app.worker.tasks module
celery_app.autodiscover_tasks(["app.worker.tasks"])


celery_app.conf.beat_schedule = {
    "example-every-minute": {
        "task": "app.worker.tasks.examples.example_task",
        "schedule": 60.0,  # Every 60 seconds
        "args": ("periodic",),
    },
    # Example with crontab (runs at 00:00 every day)
    # "daily-cleanup": {
    #     "task": "app.worker.tasks.examples.cleanup_task",
    #     "schedule": crontab(hour=0, minute=0),
    # },
}

{%- if cookiecutter.enable_rag %}
celery_app.conf.beat_schedule["rag-sync-check"] = {
    "task": "app.worker.tasks.rag_tasks.check_scheduled_syncs",
    "schedule": 60.0,  # Every 60 seconds
}
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_billing %}
celery_app.conf.beat_schedule["send-trial-reminders"] = {
    "task": "app.worker.tasks.email_tasks.send_trial_reminders_task",
    "schedule": crontab(hour=9, minute=0),  # Daily at 09:00
}
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_credits_system %}
celery_app.conf.beat_schedule["send-low-credits-alerts"] = {
    "task": "app.worker.tasks.email_tasks.send_low_credits_alerts_task",
    "schedule": crontab(minute=0, hour="*/4"),  # Every 4 hours
}
{%- endif %}
{%- if cookiecutter.enable_credits_system %}
celery_app.conf.beat_schedule["cleanup-usage-events"] = {
    "task": "app.worker.tasks.cleanup_tasks.cleanup_usage_events_task",
    "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Weekly Sunday 03:00
}
{%- endif %}

{%- if cookiecutter.enable_logfire and cookiecutter.logfire_celery %}


# Instrument Celery with Logfire
instrument_celery()
{%- endif %}
{%- else %}
# Celery not enabled for this project
{%- endif %}
