import pytest
from langchain_text_splitters import RecursiveCharacterTextSplitter


class TestRecursiveChunking:

    def test_splits_long_text(self):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=100,
            chunk_overlap=20,
        )
        text = "This is a test sentence. " * 20
        
        docs = splitter.create_documents([text])
        
        assert len(docs) > 1
        for doc in docs:
            assert len(doc.page_content) <= 100

    def test_handles_empty_text(self):
        splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
        
        docs = splitter.create_documents([""])
        
        assert len(docs) >= 0  # Empty text returns empty list
        assert len(docs) == 0  # Empty text returns empty list

    def test_handles_short_text(self):
        splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
        text = "Short text"
        
        docs = splitter.create_documents([text])
        
        assert len(docs) == 1
        assert docs[0].page_content == text
        