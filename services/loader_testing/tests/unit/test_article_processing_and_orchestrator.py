# services/loader_faster/tests/unit/test_article_processing_and_orchestrator.py

import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def mock_db_url(monkeypatch):
    # Needed so loader.DB_URL doesn't crash at import
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake")


def test_create_chunks_dataframe_and_process_article():
    from api.loader import Article, ArticleProcessor, ChunkingStrategy

    # --- Dummy strategy & embedder to avoid external dependencies ----------
    class DummyChunking(ChunkingStrategy):
        def chunk_text(self, text: str):
            return ["chunk-1", "chunk-2"]

    class DummyEmbedder:
        def __init__(self):
            self.calls = []

        def embed_documents(self, texts):
            self.calls.append(texts)
            # Return some fake vectors
            return [[0.1, 0.2], [0.3, 0.4]]

    article = Article(
        id=1,
        author="Author",
        title="Title",
        summary="Summary",
        content="Some long content",
        source_link="http://example.com",
        source_type="rss",
        fetched_at="fetched",
        published_at="published",
        vflag=0,
        article_id="article-1",
    )

    processor = ArticleProcessor(DummyChunking(), DummyEmbedder())

    # _create_chunks_dataframe
    chunks = ["chunk-1", "chunk-2"]
    df = processor._create_chunks_dataframe(article, chunks)
    assert list(df["chunk"]) == chunks
    assert list(df["article_id"]) == ["article-1", "article-1"]
    assert df["title"].iloc[0] == "Title"

    # process_article (uses both chunking and embedding)
    df2 = processor.process_article(article, article_num=1, total=1)
    assert len(df2) == 2
    assert "embedding" in df2.columns
    assert all(isinstance(e, list) for e in df2["embedding"])


def test_chunk_embed_load_orchestrates(monkeypatch):
    from api import loader as loader_mod

    # --- Fake components to avoid real DB and Vertex -----------------------
    class FakeEmbedder:
        def __init__(self):
            self.dim = 768

        def embed_documents(self, texts):
            # Just return a constant vector
            return [[0.0] * 3 for _ in texts]

    class FakeProcessor:
        def __init__(self, chunking_strategy, embedder):
            self.calls = []

        def process_article(self, article, article_num, total):
            self.calls.append((article.article_id, article_num, total))
            # Return a tiny DataFrame compatible with insert_chunks of FakeDB
            return pd.DataFrame(
                [
                    {
                        "chunk": "c1",
                        "chunk_index": 0,
                        "embedding": [0.0, 0.1, 0.2],
                        "article_id": article.article_id,
                    }
                ]
            )

    class FakeDBManager:
        def __init__(self, db_url):
            self.db_url = db_url
            self.inserted = []
            self.marked = []
            # Build two fake articles
            self._articles = [
                loader_mod.Article(
                    id=1,
                    author="A1",
                    title="T1",
                    summary="S1",
                    content="C1",
                    source_link="L1",
                    source_type="rss",
                    fetched_at="f1",
                    published_at="p1",
                    vflag=0,
                    article_id="article-1",
                ),
                loader_mod.Article(
                    id=2,
                    author="A2",
                    title="T2",
                    summary="S2",
                    content="C2",
                    source_link="L2",
                    source_type="rss",
                    fetched_at="f2",
                    published_at="p2",
                    vflag=0,
                    article_id="article-2",
                ),
            ]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def fetch_unprocessed_articles(self):
            return self._articles

        def insert_chunks(self, df):
            self.inserted.append(df)
            return len(df)

        def mark_article_processed(self, article_id):
            self.marked.append(article_id)

    # Patch the heavy classes inside loader
    monkeypatch.setattr(loader_mod, "VertexEmbeddings", FakeEmbedder)
    monkeypatch.setattr(loader_mod, "ArticleProcessor", FakeProcessor)
    monkeypatch.setattr(loader_mod, "DatabaseManager", FakeDBManager)

    # --- Call the orchestration function -----------------------------------
    result = loader_mod.chunk_embed_load(method="char-split")

    assert result["status"] == "success"
    assert result["processed"] == 2
    assert result["total_found"] == 2
