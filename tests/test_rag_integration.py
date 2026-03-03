"""Integration tests for RAG-enabled project generation.

These tests generate projects with RAG configuration and verify
the correct files and settings are created.
"""

import re
from pathlib import Path

import pytest

from fastapi_gen.config import (
    AIFrameworkType,
    AuthType,
    BackgroundTaskType,
    DatabaseType,
    EmbeddingProviderType,
    LLMProviderType,
    PdfParserType,
    ProjectConfig,
    RAGFeatures,
    RerankerType,
)
from fastapi_gen.generator import generate_project


class TestRAGProjectGeneration:
    """Integration tests for RAG project generation."""

    @pytest.fixture
    def rag_project_celery(self, tmp_path: Path) -> Path:
        """Generate a RAG project with Celery."""
        config = ProjectConfig(
            project_name="rag_celery",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        return generate_project(config, tmp_path)

    @pytest.fixture
    def rag_project_taskiq(self, tmp_path: Path) -> Path:
        """Generate a RAG project with TaskIQ."""
        config = ProjectConfig(
            project_name="rag_taskiq",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            background_tasks=BackgroundTaskType.TASKIQ,
            enable_redis=True,
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        return generate_project(config, tmp_path)

    @pytest.fixture
    def rag_project_arq(self, tmp_path: Path) -> Path:
        """Generate a RAG project with ARQ."""
        config = ProjectConfig(
            project_name="rag_arq",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            background_tasks=BackgroundTaskType.ARQ,
            enable_redis=True,
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        return generate_project(config, tmp_path)


class TestRAGFilesExist:
    """Tests that RAG files are created when RAG is enabled."""

    @pytest.fixture
    def rag_project(self, tmp_path: Path) -> Path:
        """Generate a RAG project with Celery."""
        config = ProjectConfig(
            project_name="rag_files_test",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        return generate_project(config, tmp_path)

    def test_rag_config_exists(self, rag_project) -> None:
        """Test that rag/config.py exists."""
        rag_config = rag_project / "backend" / "app" / "rag" / "config.py"
        assert rag_config.exists(), "rag/config.py should exist when RAG is enabled"

    def test_rag_documents_exists(self, rag_project) -> None:
        """Test that rag/documents.py exists."""
        rag_docs = rag_project / "backend" / "app" / "rag" / "documents.py"
        assert rag_docs.exists(), "rag/documents.py should exist when RAG is enabled"

    def test_rag_embeddings_exists(self, rag_project) -> None:
        """Test that rag/embeddings.py exists."""
        rag_embeddings = rag_project / "backend" / "app" / "rag" / "embeddings.py"
        assert rag_embeddings.exists(), "rag/embeddings.py should exist when RAG is enabled"

    def test_rag_ingestion_exists(self, rag_project) -> None:
        """Test that rag/ingestion.py exists."""
        rag_ingestion = rag_project / "backend" / "app" / "rag" / "ingestion.py"
        assert rag_ingestion.exists(), "rag/ingestion.py should exist when RAG is enabled"

    def test_rag_retrieval_exists(self, rag_project) -> None:
        """Test that rag/retrieval.py exists."""
        rag_retrieval = rag_project / "backend" / "app" / "rag" / "retrieval.py"
        assert rag_retrieval.exists(), "rag/retrieval.py should exist when RAG is enabled"

    def test_rag_vectorstore_exists(self, rag_project) -> None:
        """Test that rag/vectorstore.py exists."""
        rag_vectorstore = rag_project / "backend" / "app" / "rag" / "vectorstore.py"
        assert rag_vectorstore.exists(), "rag/vectorstore.py should exist when RAG is enabled"

    def test_rag_api_route_exists(self, rag_project) -> None:
        """Test that rag API route exists."""
        rag_api = rag_project / "backend" / "app" / "api" / "routes" / "v1" / "rag.py"
        assert rag_api.exists(), "rag.py API route should exist when RAG is enabled"

    def test_rag_tool_exists(self, rag_project) -> None:
        """Test that rag_tool.py exists in agents."""
        rag_tool = rag_project / "backend" / "app" / "agents" / "tools" / "rag_tool.py"
        assert rag_tool.exists(), "rag_tool.py should exist when RAG is enabled"

    def test_rag_tasks_exist(self, rag_project) -> None:
        """Test that rag_ingestion.py tasks exist."""
        rag_tasks = rag_project / "backend" / "app" / "worker" / "tasks" / "rag_ingestion.py"
        assert rag_tasks.exists(), "rag_ingestion.py should exist when RAG is enabled"

    def test_docker_compose_has_milvus(self, rag_project) -> None:
        """Test that docker-compose.yml has Milvus service."""
        docker_compose = rag_project / "docker-compose.yml"
        content = docker_compose.read_text()
        # Use regex to match YAML service definition (with possible leading whitespace)
        assert re.search(r"^\s*milvus:", content, re.MULTILINE), \
            "docker-compose.yml should have milvus service"


class TestNonRAGProjectNoRAGFiles:
    """Tests that RAG files are NOT created when RAG is disabled."""

    @pytest.fixture
    def non_rag_project(self, tmp_path: Path) -> Path:
        """Generate a non-RAG project."""
        config = ProjectConfig(
            project_name="no_rag_project",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=False),
            enable_docker=True,
        )
        return generate_project(config, tmp_path)

    def test_rag_folder_not_exists(self, non_rag_project) -> None:
        """Test that rag/ folder does not exist."""
        rag_dir = non_rag_project / "backend" / "app" / "rag"
        assert not rag_dir.exists(), "rag/ folder should not exist when RAG is disabled"

    def test_rag_api_not_exists(self, non_rag_project) -> None:
        """Test that rag API route does not exist."""
        rag_api = non_rag_project / "backend" / "app" / "api" / "routes" / "v1" / "rag.py"
        assert not rag_api.exists(), "rag.py should not exist when RAG is disabled"


class TestRAGWithDifferentBackgroundTasks:
    """Tests for RAG with different background task systems."""

    def test_rag_celery_has_reindex_task(self, tmp_path) -> None:
        """Test that Celery RAG project has reindex task."""
        config = ProjectConfig(
            project_name="rag_celery_task",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)
        rag_tasks = project / "backend" / "app" / "worker" / "tasks" / "rag_ingestion.py"
        content = rag_tasks.read_text()
        # Use word boundary to avoid false matches
        assert re.search(r"\bshared_task\b", content), \
            "Celery project should have @shared_task decorator"

    def test_rag_taskiq_has_reindex_task(self, tmp_path) -> None:
        """Test that TaskIQ RAG project has reindex task."""
        config = ProjectConfig(
            project_name="rag_taskiq_task",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            background_tasks=BackgroundTaskType.TASKIQ,
            enable_redis=True,
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)
        rag_tasks = project / "backend" / "app" / "worker" / "tasks" / "rag_ingestion.py"
        content = rag_tasks.read_text()
        # Use regex to match broker.task or @broker decorator
        assert re.search(r"(broker\.task|@broker)", content), \
            "TaskIQ project should have @broker.task decorator"

    def test_rag_arq_has_reindex_task(self, tmp_path) -> None:
        """Test that ARQ RAG project has reindex task."""
        config = ProjectConfig(
            project_name="rag_arq_task",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            background_tasks=BackgroundTaskType.ARQ,
            enable_redis=True,
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)
        rag_tasks = project / "backend" / "app" / "worker" / "tasks" / "rag_ingestion.py"
        content = rag_tasks.read_text()
        # Use word boundary to avoid false matches
        assert re.search(r"\breindex_collection_arq\b", content), \
            "ARQ project should have reindex_collection_arq function"


class TestRAGWithAIFrameworks:
    """Tests for RAG with different AI frameworks."""

    @pytest.mark.parametrize("framework", [
        AIFrameworkType.PYDANTIC_AI,
        AIFrameworkType.LANGCHAIN,
        AIFrameworkType.LANGGRAPH,
        # Skip CrewAI - template has pre-existing bug with user_input
        AIFrameworkType.DEEPAGENTS,
    ])
    def test_rag_with_ai_framework(self, tmp_path, framework) -> None:
        """Test that RAG works with all AI frameworks."""
        # Skip LangChain/LangGraph/CrewAI/DeepAgents with OpenRouter (not supported)
        llm_provider = LLMProviderType.OPENAI
        if framework in (AIFrameworkType.LANGCHAIN, AIFrameworkType.LANGGRAPH, 
                        AIFrameworkType.CREWAI, AIFrameworkType.DEEPAGENTS):
            llm_provider = LLMProviderType.OPENAI

        config = ProjectConfig(
            project_name=f"rag_{framework.value}",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_ai_agent=True,
            ai_framework=framework,
            llm_provider=llm_provider,
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)
        
        # Verify RAG files exist
        rag_dir = project / "backend" / "app" / "rag"
        assert rag_dir.exists(), f"RAG should be enabled with {framework.value}"


class TestRAGWithEmbeddingProviders:
    """Tests for RAG with different embedding providers."""

    def test_rag_with_openai_embeddings(self, tmp_path) -> None:
        """Test RAG with OpenAI embeddings."""
        config = ProjectConfig(
            project_name="rag_openai_emb",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_ai_agent=True,
            llm_provider=LLMProviderType.OPENAI,
            rag_features=RAGFeatures(enable_rag=True),
            embedding_provider=EmbeddingProviderType.OPENAI,
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)
        
        # Verify config has correct embedding settings
        rag_config = project / "backend" / "app" / "rag" / "config.py"
        content = rag_config.read_text()
        assert "text-embedding-3-small" in content or "embedding-3" in content

    def test_rag_with_voyage_embeddings(self, tmp_path) -> None:
        """Test RAG with Voyage embeddings (auto-derived from Anthropic)."""
        config = ProjectConfig(
            project_name="rag_voyage_emb",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_ai_agent=True,
            llm_provider=LLMProviderType.ANTHROPIC,  # Derives Voyage
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)
        
        # Verify config has Voyage settings
        rag_config = project / "backend" / "app" / "rag" / "config.py"
        content = rag_config.read_text()
        assert "voyage" in content.lower()

    def test_rag_with_sentence_transformers(self, tmp_path) -> None:
        """Test RAG with SentenceTransformers (auto-derived from OpenRouter)."""
        config = ProjectConfig(
            project_name="rag_st_emb",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_ai_agent=True,
            llm_provider=LLMProviderType.OPENROUTER,  # Derives SentenceTransformers
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)
        
        # Verify config has SentenceTransformers settings
        rag_config = project / "backend" / "app" / "rag" / "config.py"
        content = rag_config.read_text()
        assert "sentence" in content.lower() or "all-MiniLM" in content


class TestRAGWithRerankers:
    """Tests for RAG with different reranker options."""

    def test_rag_no_reranker(self, tmp_path) -> None:
        """Test RAG without reranker."""
        config = ProjectConfig(
            project_name="rag_no_rerank",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True, enable_reranker=False),
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)
        
        rag_config = project / "backend" / "app" / "rag" / "config.py"
        content = rag_config.read_text()
        # Should not have reranker config
        assert "RerankerConfig" not in content

    def test_rag_with_cohere_reranker(self, tmp_path) -> None:
        """Test RAG with Cohere reranker."""
        config = ProjectConfig(
            project_name="rag_cohere_rerank",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True, enable_reranker=True),
            reranker=RerankerType.COHERE,
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)
        
        rag_config = project / "backend" / "app" / "rag" / "config.py"
        content = rag_config.read_text()
        assert "cohere" in content.lower() or "reranker" in content.lower()

    def test_rag_with_cross_encoder_reranker(self, tmp_path) -> None:
        """Test RAG with CrossEncoder reranker."""
        config = ProjectConfig(
            project_name="rag_ce_rerank",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_ai_agent=True,
            llm_provider=LLMProviderType.OPENROUTER,  # Derives CrossEncoder
            rag_features=RAGFeatures(enable_rag=True, enable_reranker=True),
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)
        
        rag_config = project / "backend" / "app" / "rag" / "config.py"
        content = rag_config.read_text()
        assert "cross" in content.lower() or "reranker" in content.lower()


class TestRAGWithPDFParsers:
    """Tests for RAG with different PDF parsers."""

    def test_rag_with_pdfplumber(self, tmp_path) -> None:
        """Test RAG with pdfplumber parser."""
        config = ProjectConfig(
            project_name="rag_pdfplumber",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True),
            pdf_parser=PdfParserType.PDFPLUMBER,
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)
        
        rag_config = project / "backend" / "app" / "rag" / "config.py"
        content = rag_config.read_text()
        assert "pdfplumber" in content.lower()

    def test_rag_with_llamaparse(self, tmp_path) -> None:
        """Test RAG with LlamaParse parser."""
        config = ProjectConfig(
            project_name="rag_llamaparse",
            database=DatabaseType.POSTGRESQL,
            auth=AuthType.JWT,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True),
            pdf_parser=PdfParserType.LLAMAPARSE,
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)
        
        rag_config = project / "backend" / "app" / "rag" / "config.py"
        content = rag_config.read_text()
        assert "llamaparse" in content.lower()


class TestRAGValidation:
    """Tests for RAG configuration validation."""

    def test_rag_requires_ai_agent(self) -> None:
        """Test that RAG requires AI agent."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError, match="RAG requires AI agent"):
            ProjectConfig(
                project_name="rag_no_agent",
                database=DatabaseType.POSTGRESQL,
                auth=AuthType.JWT,
                background_tasks=BackgroundTaskType.CELERY,
                enable_redis=True,
                enable_ai_agent=False,
                rag_features=RAGFeatures(enable_rag=True),
                enable_docker=True,
            )

    def test_rag_requires_background_tasks(self) -> None:
        """Test that RAG requires background tasks."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError, match="background task system"):
            ProjectConfig(
                project_name="rag_no_bg",
                database=DatabaseType.POSTGRESQL,
                auth=AuthType.JWT,
                background_tasks=BackgroundTaskType.NONE,
                enable_redis=True,
                enable_ai_agent=True,
                rag_features=RAGFeatures(enable_rag=True),
                enable_docker=True,
            )

    def test_rag_requires_docker(self) -> None:
        """Test that RAG requires Docker."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError, match="requires Docker"):
            ProjectConfig(
                project_name="rag_no_docker",
                database=DatabaseType.POSTGRESQL,
                auth=AuthType.JWT,
                background_tasks=BackgroundTaskType.CELERY,
                enable_redis=True,
                enable_ai_agent=True,
                rag_features=RAGFeatures(enable_rag=True),
                enable_docker=False,
            )
