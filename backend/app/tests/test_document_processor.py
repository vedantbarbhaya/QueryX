import pytest
from pathlib import Path
from backend.app.config import KNOWLEDGE_BASE_DIR
from backend.app.crawler.document_processor import DocumentProcessor

def test_list_get_and_delete(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.app.config.KNOWLEDGE_BASE_DIR", tmp_path)
    # Write a dummy markdown file
    file = tmp_path / "doc1.md"
    file.write_text("# Doc1\nContent")
    processor = DocumentProcessor()
    docs = processor.list_documents()
    assert len(docs) == 1
    assert docs[0]["id"] == "doc1"
    content = processor.get_document_content("doc1")
    assert "# Doc1" in content
    assert processor.delete_document("doc1")
    assert not file.exists()