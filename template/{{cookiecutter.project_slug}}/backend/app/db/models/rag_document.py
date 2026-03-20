{%- if cookiecutter.enable_rag and cookiecutter.enable_conversation_persistence %}
{%- if cookiecutter.use_postgresql and cookiecutter.use_sqlmodel %}
"""RAGDocument model — tracks documents ingested into RAG collections."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin


class RAGDocument(TimestampMixin, SQLModel, table=True):
    """Tracks ingested documents with processing status."""

    __tablename__ = "rag_documents"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True),
    )
    collection_name: str = Field(sa_column=Column(String(255), nullable=False, index=True))
    filename: str = Field(sa_column=Column(String(255), nullable=False))
    filesize: int = Field(sa_column=Column(Integer, nullable=False, default=0))
    filetype: str = Field(sa_column=Column(String(20), nullable=False))
    storage_path: str | None = Field(default=None, sa_column=Column(String(500), nullable=True))
    status: str = Field(default="processing", sa_column=Column(String(20), nullable=False, default="processing"))
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    vector_document_id: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    chunk_count: int = Field(default=0, sa_column=Column(Integer, nullable=False, default=0))
    started_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    completed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    def __repr__(self) -> str:
        return f"<RAGDocument(id={self.id}, filename={self.filename}, status={self.status})>"
{%- endif %}
{%- endif %}
