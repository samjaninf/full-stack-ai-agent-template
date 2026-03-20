{%- if cookiecutter.use_taskiq %}
"""Taskiq scheduled tasks (cron-like)."""

from app.worker.taskiq_app import broker
from app.worker.tasks.taskiq_examples import example_task


# Define scheduled tasks using labels
# These are picked up by the scheduler

@broker.task(schedule=[{"cron": "* * * * *"}])  # Every minute
async def scheduled_example() -> dict:
    """Example scheduled task that runs every minute."""
    result = await example_task.kiq("scheduled")
    return {"scheduled": True, "task_id": str(result.task_id)}


# Alternative: Define schedules in scheduler source
# The scheduler will read these when started with --source flag
SCHEDULES = [
    {
        "task": "app.worker.tasks.taskiq_examples:example_task",
        "cron": "*/5 * * * *",  # Every 5 minutes
        "args": ["periodic-5min"],
    },
]
{%- else %}
# Taskiq not enabled for this project
{%- endif %}
