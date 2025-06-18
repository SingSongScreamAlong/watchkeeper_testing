"""
Base collector for WATCHKEEPER Testing Edition.

This module provides the base framework for news collection.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup
import feedparser

from src.core.logging import logger


class BaseCollector(ABC):
    """
    Base collector class for all news sources.
    
    Provides common functionality for news collection.
    """
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize the collector.
        
        Args:
            session: Optional aiohttp session to use.
        """
        self.session = session
        self.name = "base"
        self.source_url = ""
        self.source_type = ""
        self.language = "en"
        self.max_articles = 10
        self.request_timeout = 30
        self.request_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }
    
    async def ensure_session(self):
        """Ensure an aiohttp session exists."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        """Close the aiohttp session if it was created by this collector."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    @abstractmethod
    async def collect(self) -> List[Dict[str, Any]]:
        """
        Collect articles from the source.
        
        Returns:
            List of collected articles.
        """
        pass
    
    async def fetch_url(self, url: str) -> Optional[str]:
        """
        Fetch content from a URL.
        
        Args:
            url: URL to fetch.
            
        Returns:
            HTML content or None if failed.
        """
        await self.ensure_session()
        
        try:
            async with self.session.get(
                url, 
                headers=self.request_headers, 
                timeout=self.request_timeout
            ) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch URL: {url}, status: {response.status}")
                    return None
                
                return await response.text()
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}")
            return None
    
    async def parse_rss_feed(self, feed_url: str) -> List[Dict[str, Any]]:
        """
        Parse an RSS feed.
        
        Args:
            feed_url: URL of the RSS feed.
            
        Returns:
            List of articles from the feed.
        """
        try:
            # Fetch feed content
            feed_content = await self.fetch_url(feed_url)
            if not feed_content:
                return []
            
            # Parse feed
            feed = feedparser.parse(feed_content)
            
            if not feed.entries:
                logger.warning(f"No entries found in feed: {feed_url}")
                return []
            
            # Process entries
            articles = []
            for entry in feed.entries[:self.max_articles]:
                try:
                    # Extract basic data
                    article = {
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "published_at": entry.get("published", ""),
                        "source_name": self.name,
                        "source_url": self.source_url,
                        "language": self.language,
                        "content": "",
                        "summary": entry.get("summary", "")
                    }
                    
                    # Skip if no URL
                    if not article["url"]:
                        continue
                    
                    articles.append(article)
                    
                except Exception as e:
                    logger.error(f"Error processing feed entry: {e}")
            
            return articles
            
        except Exception as e:
            logger.error(f"Error parsing RSS feed {feed_url}: {e}")
            return []
    
    async def extract_article_content(self, url: str, content_selectors: List[str]) -> Optional[str]:
        """
        Extract article content from a URL.
        
        Args:
            url: URL to extract content from.
            content_selectors: CSS selectors for content elements.
            
        Returns:
            Article content or None if failed.
        """
        html = await self.fetch_url(url)
        if not html:
            return None
        
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Extract content based on selectors
            content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                for element in elements:
                    content += element.get_text(separator="\n", strip=True) + "\n\n"
            
            # Clean up content
            content = content.strip()
            
            return content if content else None
            
        except Exception as e:
            logger.error(f"Error extracting article content from {url}: {e}")
            return None
    
    async def extract_articles_from_page(
        self, 
        url: str, 
        article_selector: str,
        title_selector: str,
        link_selector: str,
        url_attribute: str = "href"
    ) -> List[Dict[str, Any]]:
        """
        Extract articles from a page.
        
        Args:
            url: URL to extract articles from.
            article_selector: CSS selector for article elements.
            title_selector: CSS selector for title elements.
            link_selector: CSS selector for link elements.
            url_attribute: Attribute containing the URL.
            
        Returns:
            List of articles.
        """
        html = await self.fetch_url(url)
        if not html:
            return []
        
        try:
            soup = BeautifulSoup(html, "html.parser")
            articles = []
            
            # Find article elements
            article_elements = soup.select(article_selector)
            
            for element in article_elements[:self.max_articles]:
                try:
                    # Extract title
                    title_element = element.select_one(title_selector)
                    title = title_element.get_text(strip=True) if title_element else ""
                    
                    # Extract link
                    link_element = element.select_one(link_selector) if link_selector else title_element
                    link = link_element.get(url_attribute, "") if link_element else ""
                    
                    # Make relative URLs absolute
                    if link and link.startswith("/"):
                        from urllib.parse import urljoin
                        link = urljoin(url, link)
                    
                    # Skip if no title or link
                    if not title or not link:
                        continue
                    
                    # Create article
                    article = {
                        "title": title,
                        "url": link,
                        "published_at": datetime.utcnow().isoformat(),
                        "source_name": self.name,
                        "source_url": self.source_url,
                        "language": self.language,
                        "content": "",
                        "summary": ""
                    }
                    
                    articles.append(article)
                    
                except Exception as e:
                    logger.error(f"Error extracting article from element: {e}")
            
            return articles
            
        except Exception as e:
            logger.error(f"Error extracting articles from page {url}: {e}")
            return []
