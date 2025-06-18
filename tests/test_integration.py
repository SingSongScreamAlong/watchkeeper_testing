"""
Integration tests for the WATCHKEEPER Testing Edition.

This module contains integration tests that verify the interaction between
different components of the system.
"""

import os
import sys
import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import json
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import app
from src.core.config import settings
from src.core.database import Base, get_db
from src.models.threat import Threat
from src.models.source import Source
from src.services.news_collector import TestingCollectionManager
from src.services.ai_processor import AIProcessor


# Create a test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# Override the database dependency
async def override_get_db():
    """Override the database dependency for testing."""
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Override the app dependency
app.dependency_overrides[get_db] = override_get_db


class TestAPIIntegration(unittest.TestCase):
    """Integration tests for the API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        self.api_key = "test-api-key"
        self.headers = {"X-API-Key": self.api_key}
        
        # Mock the API key settings
        settings.API_KEY = self.api_key
    
    def test_health_endpoint(self):
        """Test the health endpoint."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["status"])
        self.assertIn("timestamp", data)
        self.assertIn("version", data)
    
    def test_threats_endpoint_auth(self):
        """Test that threats endpoint requires authentication."""
        # Without API key
        response = self.client.get("/api/threats")
        self.assertEqual(response.status_code, 401)
        
        # With invalid API key
        response = self.client.get("/api/threats", headers={"X-API-Key": "invalid-key"})
        self.assertEqual(response.status_code, 401)
        
        # With valid API key (should return empty list since DB is empty)
        response = self.client.get("/api/threats", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"items": [], "total": 0})
    
    @patch("src.api.testing.collection_manager")
    def test_trigger_collection_endpoint(self, mock_collection_manager):
        """Test the trigger collection endpoint."""
        # Mock the collection manager
        mock_collection_manager.run_collection.return_value = asyncio.Future()
        mock_collection_manager.run_collection.return_value.set_result({
            "success": True,
            "articles_processed": 5,
            "threats_found": 2,
            "sources": ["BBC", "Reuters"]
        })
        
        # Test the endpoint
        response = self.client.post("/api/testing/trigger-collection", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["articles_processed"], 5)
        self.assertEqual(data["threats_found"], 2)
        self.assertEqual(data["sources"], ["BBC", "Reuters"])
        
        # Test without API key
        response = self.client.post("/api/testing/trigger-collection")
        self.assertEqual(response.status_code, 401)


class TestCollectionIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for the collection process."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        # Create test database
        self.engine = create_async_engine(TEST_DATABASE_URL)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Create test sources
        async with self.async_session() as session:
            sources = [
                Source(
                    name="BBC Test",
                    url="https://www.bbc.com/news/world/europe",
                    type="web_scrape",
                    language="en",
                    active=True
                ),
                Source(
                    name="Reuters Test",
                    url="https://www.reuters.com/world/europe/",
                    type="web_scrape",
                    language="en",
                    active=True
                )
            ]
            session.add_all(sources)
            await session.commit()
        
        # Create collection manager with mocks
        self.collection_manager = TestingCollectionManager()
        self.collection_manager.get_db = AsyncMock()
        self.collection_manager.get_db.return_value.__aenter__.return_value = self.async_session()
        self.collection_manager.get_db.return_value.__aexit__.return_value = None
        
        # Mock the collectors
        self.mock_bbc_collector = AsyncMock()
        self.mock_reuters_collector = AsyncMock()
        self.collection_manager.collectors = {
            "BBC Test": self.mock_bbc_collector,
            "Reuters Test": self.mock_reuters_collector
        }
        
        # Mock the AI processor
        self.mock_ai_processor = AsyncMock()
        self.collection_manager.ai_processor = self.mock_ai_processor
    
    async def asyncTearDown(self):
        """Tear down test fixtures."""
        # Drop test database
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    async def test_collection_process(self):
        """Test the entire collection process."""
        # Mock the collectors to return test articles
        self.mock_bbc_collector.collect.return_value = [
            {
                "title": "Test BBC Article 1",
                "content": "This is a test article about a political threat in Europe.",
                "url": "https://example.com/bbc1",
                "published_date": "2025-06-18T10:00:00Z"
            },
            {
                "title": "Test BBC Article 2",
                "content": "This is another test article with no threats.",
                "url": "https://example.com/bbc2",
                "published_date": "2025-06-18T11:00:00Z"
            }
        ]
        
        self.mock_reuters_collector.collect.return_value = [
            {
                "title": "Test Reuters Article",
                "content": "This is a test article about an economic threat in Europe.",
                "url": "https://example.com/reuters1",
                "published_date": "2025-06-18T12:00:00Z"
            }
        ]
        
        # Mock the AI processor to identify threats
        self.mock_ai_processor.analyze_article.side_effect = [
            # BBC Article 1 - threat
            {
                "is_threat": True,
                "threat_level": "medium",
                "category": "political",
                "summary": "Political threat in Europe",
                "keywords": ["political", "europe", "threat"],
                "locations": ["Europe"],
                "confidence": 0.85
            },
            # BBC Article 2 - not a threat
            {
                "is_threat": False,
                "confidence": 0.90
            },
            # Reuters Article - threat
            {
                "is_threat": True,
                "threat_level": "high",
                "category": "economic",
                "summary": "Economic threat in Europe",
                "keywords": ["economic", "europe", "threat"],
                "locations": ["Europe", "Germany"],
                "confidence": 0.95
            }
        ]
        
        # Mock the broadcast function
        self.collection_manager.broadcast_threat = AsyncMock()
        
        # Run the collection
        result = await self.collection_manager.run_collection()
        
        # Assertions
        self.assertTrue(result["success"])
        self.assertEqual(result["articles_processed"], 3)
        self.assertEqual(result["threats_found"], 2)
        self.assertEqual(set(result["sources"]), {"BBC Test", "Reuters Test"})
        
        # Check that the collectors were called
        self.mock_bbc_collector.collect.assert_called_once()
        self.mock_reuters_collector.collect.assert_called_once()
        
        # Check that the AI processor was called for each article
        self.assertEqual(self.mock_ai_processor.analyze_article.call_count, 3)
        
        # Check that threats were broadcast
        self.assertEqual(self.collection_manager.broadcast_threat.call_count, 2)
        
        # Check that threats were saved to the database
        async with self.async_session() as session:
            threats = (await session.execute("SELECT * FROM threats")).all()
            self.assertEqual(len(threats), 2)
            
            # Check source statistics
            sources = (await session.execute("SELECT * FROM sources")).all()
            self.assertEqual(len(sources), 2)
            
            # Check that source statistics were updated
            for source in sources:
                if source.name == "BBC Test":
                    self.assertEqual(source.articles_collected, 2)
                    self.assertEqual(source.threats_found, 1)
                elif source.name == "Reuters Test":
                    self.assertEqual(source.articles_collected, 1)
                    self.assertEqual(source.threats_found, 1)


if __name__ == '__main__':
    unittest.main()
