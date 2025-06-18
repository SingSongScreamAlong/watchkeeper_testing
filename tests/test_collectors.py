"""
Tests for the collectors module.

This module contains tests for the news collectors.
"""

import os
import sys
import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import aiohttp
from aiohttp import ClientSession

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.collectors.base_collector import BaseCollector
from src.collectors.bbc_collector import BBCCollector
from src.collectors.reuters_collector import ReutersCollector
from src.collectors.dw_collector import DWCollector


class TestBaseCollector(unittest.TestCase):
    """Tests for the BaseCollector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.collector = BaseCollector()
    
    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.collector.name, "base")
        self.assertEqual(self.collector.source_url, "")
        self.assertEqual(self.collector.source_type, "")
        self.assertEqual(self.collector.language, "en")
        self.assertEqual(self.collector.max_articles, 10)
        self.assertEqual(self.collector.request_timeout, 30)
        self.assertIsNone(self.collector.session)
    
    @patch('aiohttp.ClientSession')
    def test_ensure_session(self, mock_session):
        """Test ensure_session method."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Test when session is None
        loop.run_until_complete(self.collector.ensure_session())
        self.assertIsNotNone(self.collector.session)
        
        # Test when session already exists
        old_session = self.collector.session
        loop.run_until_complete(self.collector.ensure_session())
        self.assertEqual(self.collector.session, old_session)
        
        loop.close()
    
    @patch('aiohttp.ClientSession')
    def test_close_session(self, mock_session):
        """Test close_session method."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Set up mock session
        mock_session_instance = AsyncMock()
        self.collector.session = mock_session_instance
        
        # Test closing session
        loop.run_until_complete(self.collector.close_session())
        mock_session_instance.close.assert_called_once()
        self.assertIsNone(self.collector.session)
        
        loop.close()
    
    def test_abstract_collect(self):
        """Test that collect is abstract."""
        with self.assertRaises(NotImplementedError):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.collector.collect())
            loop.close()


class TestBBCCollector(unittest.TestCase):
    """Tests for the BBCCollector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.collector = BBCCollector()
    
    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.collector.name, "BBC")
        self.assertEqual(self.collector.source_url, "https://www.bbc.com/news/world/europe")
        self.assertEqual(self.collector.source_type, "web_scrape")
        self.assertEqual(self.collector.language, "en")
        self.assertEqual(self.collector.max_articles, 10)
        self.assertEqual(self.collector.rss_url, "http://feeds.bbci.co.uk/news/world/europe/rss.xml")
    
    @patch('src.collectors.base_collector.BaseCollector.parse_rss_feed')
    @patch('src.collectors.base_collector.BaseCollector.extract_articles_from_page')
    @patch('src.collectors.base_collector.BaseCollector.extract_article_content')
    @patch('asyncio.sleep')
    async def test_collect(self, mock_sleep, mock_extract_content, mock_extract_articles, mock_parse_rss):
        """Test collect method."""
        # Set up mocks
        mock_parse_rss.return_value = [
            {"title": "Test Article 1", "url": "https://example.com/1", "content": ""},
            {"title": "Test Article 2", "url": "https://example.com/2", "content": ""}
        ]
        mock_extract_content.return_value = "Test content"
        
        # Test successful collection from RSS
        result = await self.collector.collect()
        
        # Assertions
        mock_parse_rss.assert_called_once_with(self.collector.rss_url)
        self.assertEqual(len(result), 2)
        self.assertEqual(mock_extract_content.call_count, 2)
        
        # Test fallback to web scraping
        mock_parse_rss.reset_mock()
        mock_extract_content.reset_mock()
        mock_parse_rss.return_value = []
        mock_extract_articles.return_value = [
            {"title": "Test Article 3", "url": "https://example.com/3", "content": ""},
            {"title": "Test Article 4", "url": "https://example.com/4", "content": ""}
        ]
        
        result = await self.collector.collect()
        
        mock_parse_rss.assert_called_once()
        mock_extract_articles.assert_called_once()
        self.assertEqual(len(result), 2)
        
        # Test exception handling
        mock_parse_rss.reset_mock()
        mock_extract_articles.reset_mock()
        mock_parse_rss.side_effect = Exception("Test error")
        mock_extract_articles.side_effect = Exception("Test error")
        
        result = await self.collector.collect()
        
        self.assertEqual(result, [])


class TestReutersCollector(unittest.TestCase):
    """Tests for the ReutersCollector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.collector = ReutersCollector()
    
    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.collector.name, "Reuters")
        self.assertEqual(self.collector.source_url, "https://www.reuters.com/world/europe/")
        self.assertEqual(self.collector.source_type, "web_scrape")
        self.assertEqual(self.collector.language, "en")
        self.assertEqual(self.collector.max_articles, 10)
        self.assertEqual(self.collector.rss_url, "https://www.reutersagency.com/feed/?best-regions=europe&post_type=best")


class TestDWCollector(unittest.TestCase):
    """Tests for the DWCollector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.collector = DWCollector()
    
    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.collector.name, "Deutsche Welle")
        self.assertEqual(self.collector.source_url, "https://www.dw.com/en/europe/")
        self.assertEqual(self.collector.source_type, "web_scrape")
        self.assertEqual(self.collector.language, "en")
        self.assertEqual(self.collector.max_articles, 10)
        self.assertEqual(self.collector.rss_url, "https://rss.dw.com/rdf/rss-en-eu")


if __name__ == '__main__':
    unittest.main()
