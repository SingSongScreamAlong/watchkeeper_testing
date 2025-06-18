"""
BBC collector for WATCHKEEPER Testing Edition.

This module provides a collector for BBC Europe news.
"""

import asyncio
from typing import List, Dict, Any, Optional
import aiohttp
from bs4 import BeautifulSoup

from src.core.logging import logger
from src.collectors.base_collector import BaseCollector


class BBCCollector(BaseCollector):
    """
    Collector for BBC Europe news.
    """
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize the BBC collector.
        
        Args:
            session: Optional aiohttp session to use.
        """
        super().__init__(session)
        self.name = "BBC"
        self.source_url = "https://www.bbc.com/news/world/europe"
        self.source_type = "web_scrape"
        self.language = "en"
        self.max_articles = 10
        self.rss_url = "http://feeds.bbci.co.uk/news/world/europe/rss.xml"
        
        # CSS selectors for article extraction
        self.article_selector = "article"
        self.title_selector = "h3"
        self.link_selector = "a"
        
        # CSS selectors for content extraction
        self.content_selectors = [
            "article[data-component='text-block']",
            ".article__body-content",
            "[data-component='text-block']"
        ]
    
    async def collect(self) -> List[Dict[str, Any]]:
        """
        Collect articles from BBC Europe.
        
        Returns:
            List of collected articles.
        """
        logger.info(f"Collecting articles from {self.name}")
        
        try:
            # Try RSS feed first (more reliable)
            articles = await self.parse_rss_feed(self.rss_url)
            
            # If RSS feed fails, try web scraping
            if not articles:
                logger.info(f"RSS feed failed, trying web scraping for {self.name}")
                articles = await self.extract_articles_from_page(
                    self.source_url,
                    self.article_selector,
                    self.title_selector,
                    self.link_selector
                )
            
            # Fetch full content for each article
            for article in articles:
                try:
                    content = await self.extract_article_content(
                        article["url"],
                        self.content_selectors
                    )
                    
                    if content:
                        article["content"] = content
                    
                    # Add a small delay to avoid overloading the server
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error fetching content for article {article['url']}: {e}")
            
            logger.info(f"Collected {len(articles)} articles from {self.name}")
            return articles
            
        except Exception as e:
            logger.error(f"Error collecting from {self.name}: {e}")
            return []
