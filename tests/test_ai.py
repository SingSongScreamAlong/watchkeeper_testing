"""
Tests for the AI processor module.

This module contains tests for the AI processor service.
"""

import os
import sys
import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.ai_processor import AIProcessor
from src.core.config import settings


class TestAIProcessor(unittest.TestCase):
    """Tests for the AIProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.ai_processor = AIProcessor()
    
    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.ai_processor.base_url, settings.OLLAMA_BASE_URL)
        self.assertEqual(self.ai_processor.model, settings.AI_MODEL)
        self.assertEqual(self.ai_processor.timeout, settings.AI_TIMEOUT)
        self.assertEqual(self.ai_processor.processing_delay, settings.PROCESSING_DELAY)
        self.assertIsNone(self.ai_processor.session)
    
    @patch('aiohttp.ClientSession')
    def test_ensure_session(self, mock_session):
        """Test ensure_session method."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Test when session is None
        loop.run_until_complete(self.ai_processor.ensure_session())
        self.assertIsNotNone(self.ai_processor.session)
        
        # Test when session already exists
        old_session = self.ai_processor.session
        loop.run_until_complete(self.ai_processor.ensure_session())
        self.assertEqual(self.ai_processor.session, old_session)
        
        loop.close()
    
    @patch('aiohttp.ClientSession')
    def test_close_session(self, mock_session):
        """Test close_session method."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Set up mock session
        mock_session_instance = AsyncMock()
        self.ai_processor.session = mock_session_instance
        
        # Test closing session
        loop.run_until_complete(self.ai_processor.close_session())
        mock_session_instance.close.assert_called_once()
        self.assertIsNone(self.ai_processor.session)
        
        loop.close()
    
    @patch('src.services.ai_processor.AIProcessor.ensure_session')
    @patch('asyncio.sleep')
    async def test_analyze_article(self, mock_sleep, mock_ensure_session):
        """Test analyze_article method."""
        # Set up mocks
        self.ai_processor.session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "response": json.dumps({
                "is_threat": True,
                "threat_level": "medium",
                "category": "political",
                "summary": "Test summary",
                "keywords": ["test", "threat", "political"],
                "locations": ["Europe", "Germany"],
                "confidence": 0.85
            })
        }
        self.ai_processor.session.post.return_value.__aenter__.return_value = mock_response
        
        # Test article
        article = {
            "title": "Test Article",
            "content": "This is a test article about a political threat in Europe.",
            "url": "https://example.com/article",
            "source": "Test Source"
        }
        
        # Test successful analysis
        result = await self.ai_processor.analyze_article(article)
        
        # Assertions
        mock_ensure_session.assert_called_once()
        self.ai_processor.session.post.assert_called_once()
        self.assertTrue(result["is_threat"])
        self.assertEqual(result["threat_level"], "medium")
        self.assertEqual(result["category"], "political")
        self.assertEqual(result["summary"], "Test summary")
        self.assertEqual(result["keywords"], ["test", "threat", "political"])
        self.assertEqual(result["locations"], ["Europe", "Germany"])
        self.assertEqual(result["confidence"], 0.85)
        
        # Test error handling - HTTP error
        mock_ensure_session.reset_mock()
        self.ai_processor.session.post.reset_mock()
        mock_response.status = 500
        mock_response.text.return_value = "Internal Server Error"
        
        result = await self.ai_processor.analyze_article(article)
        
        self.assertEqual(result, {
            "is_threat": False,
            "error": "Failed to get AI response: 500 Internal Server Error"
        })
        
        # Test error handling - JSON parsing error
        mock_ensure_session.reset_mock()
        self.ai_processor.session.post.reset_mock()
        mock_response.status = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        result = await self.ai_processor.analyze_article(article)
        
        self.assertEqual(result, {
            "is_threat": False,
            "error": "Failed to parse AI response"
        })
        
        # Test error handling - General exception
        mock_ensure_session.reset_mock()
        self.ai_processor.session.post.reset_mock()
        self.ai_processor.session.post.side_effect = Exception("Test error")
        
        result = await self.ai_processor.analyze_article(article)
        
        self.assertEqual(result, {
            "is_threat": False,
            "error": "AI analysis failed: Test error"
        })
    
    @patch('src.services.ai_processor.AIProcessor.ensure_session')
    async def test_check_health(self, mock_ensure_session):
        """Test check_health method."""
        # Set up mocks
        self.ai_processor.session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.2:3b", "size": 3000000000}
            ]
        }
        self.ai_processor.session.get.return_value.__aenter__.return_value = mock_response
        
        # Test successful health check
        result = await self.ai_processor.check_health()
        
        # Assertions
        mock_ensure_session.assert_called_once()
        self.ai_processor.session.get.assert_called_once()
        self.assertTrue(result["status"])
        self.assertEqual(result["model"], "llama3.2:3b")
        self.assertEqual(result["model_size"], "3.0 GB")
        
        # Test error handling - HTTP error
        mock_ensure_session.reset_mock()
        self.ai_processor.session.get.reset_mock()
        mock_response.status = 500
        mock_response.text.return_value = "Internal Server Error"
        
        result = await self.ai_processor.check_health()
        
        self.assertFalse(result["status"])
        self.assertEqual(result["error"], "Failed to connect to Ollama API: 500 Internal Server Error")
        
        # Test error handling - Model not found
        mock_ensure_session.reset_mock()
        self.ai_processor.session.get.reset_mock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "other-model", "size": 1000000000}
            ]
        }
        
        result = await self.ai_processor.check_health()
        
        self.assertFalse(result["status"])
        self.assertEqual(result["error"], f"Model {settings.AI_MODEL} not found")
        
        # Test error handling - General exception
        mock_ensure_session.reset_mock()
        self.ai_processor.session.get.reset_mock()
        self.ai_processor.session.get.side_effect = Exception("Test error")
        
        result = await self.ai_processor.check_health()
        
        self.assertFalse(result["status"])
        self.assertEqual(result["error"], "Failed to check AI health: Test error")


if __name__ == '__main__':
    unittest.main()
