"""Services layer - business logic.

Services orchestrate business operations, using repositories for data access
and raising domain exceptions for error handling.
"""
{%- set services = [] %}
{%- if cookiecutter.use_jwt or cookiecutter.include_example_crud or cookiecutter.enable_conversation_persistence or cookiecutter.enable_webhooks %}
# ruff: noqa: I001, RUF022 - Imports structured for Jinja2 template conditionals
{%- endif %}
{%- if cookiecutter.use_jwt %}
{%- set _ = services.append("UserService") %}

from app.services.user import UserService
{%- endif %}
{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}
{%- set _ = services.append("SessionService") %}

from app.services.session import SessionService
{%- endif %}
{%- if cookiecutter.include_example_crud and cookiecutter.use_database %}
{%- set _ = services.append("ItemService") %}

from app.services.item import ItemService
{%- endif %}
{%- if cookiecutter.enable_conversation_persistence and cookiecutter.use_database %}
{%- set _ = services.append("ConversationService") %}

from app.services.conversation import ConversationService
{%- endif %}
{%- if cookiecutter.enable_webhooks and cookiecutter.use_database %}
{%- set _ = services.append("WebhookService") %}

from app.services.webhook import WebhookService
{%- endif %}
{%- if cookiecutter.enable_google_drive_ingestion and cookiecutter.use_database and cookiecutter.use_milvus %}
{%- set _ = services.append("GoogleDriveIngestionService") %}

from app.services.gdrive_ingestion import GoogleDriveIngestionService
{%- endif %}
{%- if services %}

__all__ = {{ services }}
{%- endif %}
