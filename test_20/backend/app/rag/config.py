"""RAG configuration."""

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class DocumentExtensions(StrEnum):
    """Extensions supported by the RAG ingestion pipeline."""

    PDF = ".pdf"
    DOCX = ".docx"
    MD = ".md"
    TXT = ".txt"


# Known embedding models and their output dimensions.
# Used to auto-set vector store dimension from model name.
EMBEDDING_DIMENSIONS: dict[str, int] = {
    # OpenAI
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    # Voyage AI
    "voyage-3": 1024,
    "voyage-3-lite": 512,
    "voyage-code-3": 1024,
    # Google Gemini
    "gemini-embedding-exp-03-07": 3072,
    # SentenceTransformers (local)
    "all-MiniLM-L6-v2": 384,
    "all-mpnet-base-v2": 768,
    "bge-small-en-v1.5": 384,
    "bge-base-en-v1.5": 768,
    "bge-large-en-v1.5": 1024,
}


class EmbeddingsConfig(BaseModel):
    """Embeddings configuration. Dimension is auto-derived from model name."""

    model: str = "all-MiniLM-L6-v2"
    dim: int = 384

    @model_validator(mode="after")
    def set_dim_from_model(self) -> "EmbeddingsConfig":
        if self.model in EMBEDDING_DIMENSIONS:
            self.dim = EMBEDDING_DIMENSIONS[self.model]
        return self


class RerankerConfig(BaseModel):
    """Reranker configuration."""

    model: str = "cross_encoder"


class DocumentParser(BaseModel):
    """Document parsing settings (non-PDF files)."""

    method: str = "python_native"


class PdfParser(BaseModel):
    """PDF parsing settings."""

    method: str = "pymupdf"


class RAGSettings(BaseModel):
    """RAG pipeline configuration."""

    collection_name: str = "documents"

    allowed_extensions: list[DocumentExtensions] = Field(
        default_factory=lambda: list(DocumentExtensions)
    )

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 50
    chunking_strategy: str = "recursive"
    enable_hybrid_search: bool = False
    enable_ocr: bool = False

    # Embeddings
    embeddings_config: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)

    # Reranker
    reranker_config: RerankerConfig = Field(default_factory=RerankerConfig)

    # Parsers
    document_parser: DocumentParser = Field(default_factory=DocumentParser)
    pdf_parser: PdfParser = Field(default_factory=PdfParser)

    # Sources
    gdrive_ingestion: bool = True
