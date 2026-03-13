"""Repository layer for database operations."""
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite or cookiecutter.use_jwt or cookiecutter.include_example_crud or cookiecutter.enable_conversation_persistence or cookiecutter.enable_webhooks %}
# ruff: noqa: I001, RUF022 - Imports structured for Jinja2 template conditionals
{%- endif %}
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}

from app.repositories.base import BaseRepository
{%- endif %}
{%- if cookiecutter.use_jwt %}

from app.repositories import user as user_repo
{%- endif %}
{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}

from app.repositories import session as session_repo
{%- endif %}
{%- if cookiecutter.include_example_crud and cookiecutter.use_database %}

from app.repositories import item as item_repo
{%- endif %}
{%- if cookiecutter.enable_conversation_persistence and cookiecutter.use_database %}

from app.repositories import conversation as conversation_repo
{%- endif %}
{%- if cookiecutter.enable_webhooks and cookiecutter.use_database %}

from app.repositories import webhook as webhook_repo
{%- endif %}
{%- if cookiecutter.enable_google_drive_ingestion and cookiecutter.use_database %}

from app.repositories import gdrive_sync as gdrive_sync_repo
{%- endif %}

__all__ = [
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}
    "BaseRepository",
{%- endif %}
{%- if cookiecutter.use_jwt %}
    "user_repo",
{%- endif %}
{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}
    "session_repo",
{%- endif %}
{%- if cookiecutter.include_example_crud and cookiecutter.use_database %}
    "item_repo",
{%- endif %}
{%- if cookiecutter.enable_conversation_persistence and cookiecutter.use_database %}
    "conversation_repo",
{%- endif %}
{%- if cookiecutter.enable_webhooks and cookiecutter.use_database %}
    "webhook_repo",
{%- endif %}
{%- if cookiecutter.enable_google_drive_ingestion and cookiecutter.use_database %}
    "gdrive_sync_repo",
{%- endif %}
]
