import pytest
import os


@pytest.fixture(scope="session")
def db_url():
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:testpassword@localhost:5432/newsdb_test"
    )


@pytest.fixture(scope="session")
def articles_table():
    return os.environ.get("ARTICLES_TABLE_NAME", "articles_test")


@pytest.fixture(scope="session")
def vector_table():
    return os.environ.get("VECTOR_TABLE_NAME", "chunks_vector_test")


@pytest.fixture
def sample_article():
    return {
        "article_id": "test-article-123",
        "title": "Test Article Title",
        "author": "Test Author",
        "summary": "This is a test summary.",
        "content": "This is the article content. " * 100,
        "source_link": "https://example.com/article",
        "source_type": "test",
        "vflag": 0,
    }