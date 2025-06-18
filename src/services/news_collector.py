"""
News collector service for WATCHKEEPER Testing Edition.

This module provides a lightweight news collection service optimized for a 2014 Mac Mini.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import feedparser
import aiohttp
from bs4 import BeautifulSoup
import schedule
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.logging import logger
from src.core.database import SessionLocal
from src.models.source import Source
from src.services.ai_processor import ai_processor


class TestingCollectionManager:
    """
    Collection manager for WATCHKEEPER Testing Edition.
    
    Manages sequential collection and processing of news articles
    to avoid overloading older hardware.
    """
    
    def __init__(self):
        """Initialize the collection manager."""
        self.running = False
        self.session = None
        self.collection_frequency = settings.COLLECTION_FREQUENCY
        self.max_articles_per_source = settings.MAX_ARTICLES_PER_SOURCE
        self.last_collection_time = None
    
    async def initialize(self):
        """Initialize the HTTP session."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def collect_from_source(self, source: Source) -> Dict[str, Any]:
        """
        Collect articles from a source.
        
        Args:
            source: Source to collect from.
            
        Returns:
            Collection statistics.
        """
        await self.initialize()
        
        start_time = time.time()
        articles_collected = 0
        articles_processed = 0
        errors = 0
        
        try:
            logger.info(f"Collecting from {source.name} ({source.url})")
            
            # Parse RSS feed
            if source.source_type == "rss_feed":
                feed = feedparser.parse(source.url)
                
                if not feed.entries:
                    logger.warning(f"No entries found in feed: {source.url}")
                    return {
                        "source_id": source.id,
                        "source_name": source.name,
                        "articles_collected": 0,
                        "articles_processed": 0,
                        "errors": 1,
                        "duration_seconds": time.time() - start_time
                    }
                
                # Process entries (limited to max_articles_per_source)
                for entry in feed.entries[:self.max_articles_per_source]:
                    try:
                        # Extract article data
                        title = entry.get("title", "")
                        link = entry.get("link", "")
                        published = entry.get("published", "")
                        
                        # Skip if no link
                        if not link:
                            continue
                        
                        # Get full article content
                        article_content = await self._fetch_article_content(link)
                        
                        if not article_content:
                            logger.warning(f"Failed to fetch article content: {link}")
                            errors += 1
                            continue
                        
                        # Process article
                        await self._process_article(
                            title=title,
                            content=article_content,
                            url=link,
                            source_name=source.name,
                            published_at=published
                        )
                        
                        articles_collected += 1
                        articles_processed += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing article: {e}")
                        errors += 1
            
            # Web scrape
            elif source.source_type == "web_scrape":
                # This is a placeholder for web scraping logic
                # In a real implementation, this would use BeautifulSoup to scrape articles
                logger.info(f"Web scraping not fully implemented for: {source.url}")
                
                # Fetch the main page
                async with self.session.get(source.url, timeout=30) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch page: {source.url}, status: {response.status}")
                        return {
                            "source_id": source.id,
                            "source_name": source.name,
                            "articles_collected": 0,
                            "articles_processed": 0,
                            "errors": 1,
                            "duration_seconds": time.time() - start_time
                        }
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # Extract article links (this is a simplified example)
                    # In a real implementation, this would be customized for each source
                    article_links = []
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        if "article" in href or "news" in href:
                            # Make relative URLs absolute
                            if href.startswith("/"):
                                href = f"{source.url.rstrip('/')}{href}"
                            article_links.append(href)
                    
                    # Process a limited number of articles
                    for link in article_links[:self.max_articles_per_source]:
                        try:
                            # Get article content
                            article_content = await self._fetch_article_content(link)
                            
                            if not article_content:
                                logger.warning(f"Failed to fetch article content: {link}")
                                errors += 1
                                continue
                            
                            # Extract title from article page
                            article_soup = BeautifulSoup(article_content, "html.parser")
                            title = article_soup.title.string if article_soup.title else "Unknown Title"
                            
                            # Process article
                            await self._process_article(
                                title=title,
                                content=article_content,
                                url=link,
                                source_name=source.name,
                                published_at=None
                            )
                            
                            articles_collected += 1
                            articles_processed += 1
                            
                        except Exception as e:
                            logger.error(f"Error processing article: {e}")
                            errors += 1
            
            # Update source statistics
            with SessionLocal() as db:
                db_source = db.query(Source).filter(Source.id == source.id).first()
                if db_source:
                    db_source.last_collected_at = datetime.utcnow()
                    db_source.total_articles_collected += articles_collected
                    db_source.successful_collections += 1 if articles_collected > 0 else 0
                    db_source.failed_collections += 1 if articles_collected == 0 else 0
                    db.commit()
            
            logger.info(f"Collection from {source.name} complete: {articles_collected} articles collected, {errors} errors")
            
            return {
                "source_id": source.id,
                "source_name": source.name,
                "articles_collected": articles_collected,
                "articles_processed": articles_processed,
                "errors": errors,
                "duration_seconds": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Error collecting from source {source.name}: {e}")
            
            # Update source statistics for failed collection
            with SessionLocal() as db:
                db_source = db.query(Source).filter(Source.id == source.id).first()
                if db_source:
                    db_source.failed_collections += 1
                    db.commit()
            
            return {
                "source_id": source.id,
                "source_name": source.name,
                "articles_collected": 0,
                "articles_processed": 0,
                "errors": 1,
                "duration_seconds": time.time() - start_time
            }
    
    async def _fetch_article_content(self, url: str) -> Optional[str]:
        """
        Fetch article content from URL.
        
        Args:
            url: URL to fetch.
            
        Returns:
            Article content or None if failed.
        """
        try:
            async with self.session.get(url, timeout=30) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch article: {url}, status: {response.status}")
                    return None
                
                html = await response.text()
                
                # Parse HTML
                soup = BeautifulSoup(html, "html.parser")
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.extract()
                
                # Extract text
                text = soup.get_text(separator="\n", strip=True)
                
                # Clean up text
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = "\n".join(chunk for chunk in chunks if chunk)
                
                return text
                
        except Exception as e:
            logger.error(f"Error fetching article content: {e}")
            return None
    
    async def _process_article(
        self,
        title: str,
        content: str,
        url: str,
        source_name: str,
        published_at: Optional[str] = None
    ) -> bool:
        """
        Process an article with AI analysis.
        
        Args:
            title: Article title.
            content: Article content.
            url: Article URL.
            source_name: Source name.
            published_at: Publication date.
            
        Returns:
            True if processing succeeded, False otherwise.
        """
        try:
            # Prepare article text
            article_text = f"{title}\n\n{content}"
            
            # Analyze with AI
            analysis = await ai_processor.analyze_article(article_text, source_name, url)
            
            # Skip if no threat detected or low severity
            if analysis.get("severity", 0) < 2 or analysis.get("missionary_relevance", 0) < 20:
                logger.debug(f"Skipping article with low severity/relevance: {title}")
                return True
            
            # Get geolocation if country is available
            latitude, longitude = None, None
            country = analysis.get("country")
            city = analysis.get("city")
            
            if country:
                latitude, longitude = await ai_processor.get_geolocation(country, city)
            
            # Create threat in database
            with SessionLocal() as db:
                from src.models.threat import Threat, ThreatCategory, ThreatStatus
                
                # Parse published_at if available
                pub_date = None
                if published_at:
                    try:
                        # Try common date formats
                        for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z"]:
                            try:
                                pub_date = datetime.strptime(published_at, fmt)
                                break
                            except ValueError:
                                continue
                    except Exception:
                        pass
                
                # Determine category
                try:
                    category = ThreatCategory(analysis.get("category", "security_incident"))
                except ValueError:
                    category = ThreatCategory.SECURITY_INCIDENT
                
                # Determine status
                try:
                    status = ThreatStatus(analysis.get("status", "active"))
                except ValueError:
                    status = ThreatStatus.ACTIVE
                
                # Create threat
                threat = Threat(
                    title=analysis.get("title", title[:255]),
                    description=analysis.get("description", ""),
                    content=content[:10000] if content else "",  # Limit content length
                    latitude=latitude,
                    longitude=longitude,
                    country=country,
                    city=city,
                    severity=analysis.get("severity", 5),
                    category=category,
                    status=status,
                    confidence_score=analysis.get("confidence_score", 0.5),
                    missionary_relevance=analysis.get("missionary_relevance", 50),
                    source_url=url,
                    source_name=source_name,
                    published_at=pub_date,
                    processed_at=datetime.utcnow()
                )
                
                db.add(threat)
                db.commit()
                
                # Broadcast new threat via WebSocket
                try:
                    from src.api.websocket import broadcast_new_threat
                    asyncio.create_task(broadcast_new_threat(threat))
                except Exception as e:
                    logger.error(f"Failed to broadcast new threat: {e}")
                
                logger.info(f"Created new threat: {threat.id} - {threat.title}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing article: {e}")
            return False
    
    async def run_collection(self, source_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Run collection for all active sources or a specific source.
        
        Args:
            source_id: Optional source ID to collect from a specific source.
            
        Returns:
            Collection statistics.
        """
        if self.running:
            logger.warning("Collection already running, skipping")
            return {"status": "already_running"}
        
        self.running = True
        start_time = time.time()
        results = []
        
        try:
            # Get sources to collect from
            with SessionLocal() as db:
                query = db.query(Source).filter(Source.is_active == True)
                
                if source_id:
                    query = query.filter(Source.id == source_id)
                
                sources = query.all()
            
            if not sources:
                logger.warning(f"No active sources found{' for ID: ' + source_id if source_id else ''}")
                self.running = False
                return {
                    "status": "completed",
                    "sources_processed": 0,
                    "articles_collected": 0,
                    "articles_processed": 0,
                    "errors": 0,
                    "duration_seconds": time.time() - start_time
                }
            
            # Process sources sequentially to avoid overloading the system
            total_articles_collected = 0
            total_articles_processed = 0
            total_errors = 0
            
            for source in sources:
                # Check rate limiting
                if source.last_collected_at:
                    time_since_last = datetime.utcnow() - source.last_collected_at
                    min_interval = timedelta(minutes=source.collection_frequency)
                    
                    if time_since_last < min_interval and not source_id:
                        logger.info(f"Skipping {source.name}, collected {time_since_last.total_seconds() / 60:.1f} minutes ago")
                        continue
                
                # Collect from source
                result = await self.collect_from_source(source)
                results.append(result)
                
                total_articles_collected += result["articles_collected"]
                total_articles_processed += result["articles_processed"]
                total_errors += result["errors"]
                
                # Add delay between sources to avoid overloading the system
                await asyncio.sleep(2)
            
            self.last_collection_time = datetime.utcnow()
            
            logger.info(
                f"Collection complete: {len(results)} sources, "
                f"{total_articles_collected} articles collected, "
                f"{total_articles_processed} articles processed, "
                f"{total_errors} errors"
            )
            
            return {
                "status": "completed",
                "sources_processed": len(results),
                "articles_collected": total_articles_collected,
                "articles_processed": total_articles_processed,
                "errors": total_errors,
                "duration_seconds": time.time() - start_time,
                "source_results": results
            }
            
        except Exception as e:
            logger.error(f"Error running collection: {e}")
            return {
                "status": "error",
                "error": str(e),
                "duration_seconds": time.time() - start_time
            }
        finally:
            self.running = False
    
    def schedule_collections(self):
        """Schedule regular collections."""
        logger.info(f"Scheduling collections every {self.collection_frequency} minutes")
        
        # Schedule collection job
        schedule.every(self.collection_frequency).minutes.do(
            lambda: asyncio.create_task(self.run_collection())
        )


# Create global instance
collection_manager = TestingCollectionManager()
