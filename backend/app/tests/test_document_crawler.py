import pytest
import os
from pathlib import Path
from crawl4ai import AsyncWebCrawler
from backend.app.config import KNOWLEDGE_BASE_DIR
from backend.app.crawler.crawler import DocumentCrawler

class DummyResult:
    success = True
    error_message = None
    markdown = type("M", (), {"raw_markdown": "# Test\n"})()
    links = {"internal": []}

class DummyCrawler:
    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc, tb): pass
    async def arun(self, url, config): return DummyResult()

@pytest.mark.asyncio
async def test_crawl_url_success(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.app.config.KNOWLEDGE_BASE_DIR", tmp_path)
    monkeypatch.setattr("crawl4ai.AsyncWebCrawler", DummyCrawler)
    crawler = DocumentCrawler()
    result = await crawler.crawl_url("http://example.com", doc_name="testdoc")
    assert result["success"]
    assert (tmp_path / "testdoc.md").exists()