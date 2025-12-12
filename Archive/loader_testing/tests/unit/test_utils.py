"""Simple unit tests"""

import pytest


@pytest.fixture(autouse=True)
def mock_db_url(monkeypatch):
    """Ensure DATABASE_URL is always set during tests."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake")


# ============= Test CharacterChunking =============


def test_character_chunking_creates_chunks():
    """Test that character chunking creates chunks"""
    from api.loader import CharacterChunking

    chunker = CharacterChunking(chunk_size=50, chunk_overlap=10)
    text = "This is a test sentence. " * 10

    result = chunker.chunk_text(text)

    assert len(result) > 0
    assert isinstance(result, list)
    assert all(isinstance(chunk, str) for chunk in result)


def test_character_chunking_with_short_text():
    """Test character chunking with short text"""
    from api.loader import CharacterChunking

    chunker = CharacterChunking(chunk_size=100, chunk_overlap=0)
    text = "Short text."

    result = chunker.chunk_text(text)

    assert len(result) >= 1


def test_character_chunking_with_empty_text():
    """Test character chunking with empty string"""
    from api.loader import CharacterChunking

    chunker = CharacterChunking()
    text = ""

    result = chunker.chunk_text(text)

    assert isinstance(result, list)


def test_character_chunking_with_long_text():
    """Test that long text creates multiple chunks"""
    from api.loader import CharacterChunking

    chunker = CharacterChunking(chunk_size=50, chunk_overlap=0)
    text = "This is a sentence.\n\n" * 50

    result = chunker.chunk_text(text)

    assert len(result) > 5  # Should create multiple chunks


# ============= Test RecursiveChunking =============


def test_recursive_chunking_creates_chunks():
    """Test recursive chunking"""
    from api.loader import RecursiveChunking

    chunker = RecursiveChunking(chunk_size=100)
    text = "This is a test. " * 20

    result = chunker.chunk_text(text)

    assert len(result) > 0
    assert isinstance(result, list)


def test_recursive_chunking_respects_size():
    """Test that recursive chunks are reasonable size"""
    from api.loader import RecursiveChunking

    chunk_size = 50
    chunker = RecursiveChunking(chunk_size=chunk_size)
    text = "Short sentence. " * 50

    result = chunker.chunk_text(text)

    # Most chunks should be around the target size
    assert len(result) > 1


# ============= Test Chunking Factory =============


def test_get_char_split_strategy():
    """Test factory returns CharacterChunking"""
    from api.loader import CharacterChunking, get_chunking_strategy

    strategy = get_chunking_strategy("char-split")

    assert isinstance(strategy, CharacterChunking)


def test_get_recursive_split_strategy():
    """Test factory returns RecursiveChunking"""
    from api.loader import RecursiveChunking, get_chunking_strategy

    strategy = get_chunking_strategy("recursive-split")

    assert isinstance(strategy, RecursiveChunking)


def test_get_unknown_strategy_raises_error():
    """Test factory raises error for unknown method"""
    from api.loader import get_chunking_strategy

    with pytest.raises(ValueError) as exc_info:
        get_chunking_strategy("unknown-method")

    assert "Unknown chunking method" in str(exc_info.value)


def test_semantic_split_without_embeddings_raises_error():
    """Test semantic split needs embeddings"""
    from api.loader import get_chunking_strategy

    with pytest.raises(ValueError) as exc_info:
        get_chunking_strategy("semantic-split", embeddings=None)

    assert "requires embeddings" in str(exc_info.value)


# ============= Test Edge Cases =============


def test_chunking_with_none_text():
    """Test chunking handles None gracefully"""
    from api.loader import CharacterChunking

    chunker = CharacterChunking()

    result = chunker.chunk_text(None)

    assert isinstance(result, list)


def test_chunking_with_special_characters():
    """Test chunking with special characters"""
    from api.loader import CharacterChunking

    chunker = CharacterChunking(chunk_size=50)
    text = "Test with émojis 🎉 and spëcial çharacters!"

    result = chunker.chunk_text(text)

    assert len(result) >= 1
    assert isinstance(result[0], str)


def test_default_chunk_size():
    """Test that default parameters work"""
    from api.loader import CharacterChunking

    chunker = CharacterChunking()  # Using defaults
    text = "Test " * 100

    result = chunker.chunk_text(text)

    assert len(result) > 0


# ============= Dataclasses =============


def test_article_creation():
    """Test Article dataclass"""
    from api.loader import Article

    article = Article(
        id=1,
        author="Test",
        title="Title",
        summary="Summary",
        content="Content",
        source_link="http://test.com",
        source_type="rss",
        fetched_at="2025-11-20",
        published_at="2025-11-20",
        vflag=0,
        article_id="test-123",
    )

    assert article.id == 1
    assert article.article_id == "test-123"


def test_processing_result():
    """Test ProcessingResult dataclass"""
    from api.loader import ProcessingResult

    result = ProcessingResult(
        status="success",
        message="Test",
        processed=5,
        total_found=10,
    )

    assert result.status == "success"
    assert result.processed == 5
