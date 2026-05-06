"""In-process background tasks (FastAPI BackgroundTasks).

These run inside the API worker process and are dispatched via FastAPI's
``BackgroundTasks`` (or ``await``-ed directly when no distributed task queue is
configured). For distributed work — Celery/Taskiq/ARQ — see ``app.worker.tasks``.
"""
