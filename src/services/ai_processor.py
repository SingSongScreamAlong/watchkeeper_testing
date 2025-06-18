"""
AI processor service for WATCHKEEPER Testing Edition.

This module provides integration with Ollama Llama 3.2 3B model for threat analysis.
"""

import json
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
import aiohttp
import re
import nltk
from nltk.tokenize import sent_tokenize
from datetime import datetime

from src.core.config import settings
from src.core.logging import logger
from src.models.threat import Threat, ThreatCategory, ThreatStatus

# Download NLTK data if not already downloaded
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)


class AIProcessor:
    """
    AI processor for threat analysis using Ollama Llama 3.2 3B.
    
    Optimized for sequential processing on older hardware.
    """
    
    def __init__(self):
        """Initialize the AI processor."""
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.AI_MODEL
        self.timeout = settings.AI_TIMEOUT
        self.processing_delay = settings.PROCESSING_DELAY
        self.last_request_time = 0
        self.session = None
    
    async def initialize(self):
        """Initialize the aiohttp session."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _throttle_requests(self):
        """Throttle requests to avoid overloading the system."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.processing_delay:
            delay = self.processing_delay - time_since_last
            logger.debug(f"Throttling AI request for {delay:.2f} seconds")
            await asyncio.sleep(delay)
        
        self.last_request_time = time.time()
    
    async def _make_ollama_request(self, prompt: str) -> str:
        """
        Make a request to Ollama API.
        
        Args:
            prompt: The prompt to send to the model.
            
        Returns:
            The model's response.
            
        Raises:
            Exception: If the request fails.
        """
        await self.initialize()
        await self._throttle_requests()
        
        try:
            data = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for more deterministic outputs
                    "num_predict": 1024,  # Limit response length
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=data,
                timeout=self.timeout
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Ollama API error: {response.status} - {error_text}")
                    return self._fallback_analysis(prompt)
                
                result = await response.json()
                return result.get("response", "")
        
        except asyncio.TimeoutError:
            logger.error(f"Ollama request timed out after {self.timeout} seconds")
            return self._fallback_analysis(prompt)
        
        except Exception as e:
            logger.error(f"Error making Ollama request: {e}")
            return self._fallback_analysis(prompt)
    
    def _fallback_analysis(self, text: str) -> str:
        """
        Fallback analysis when AI is unavailable.
        Uses keyword matching for basic threat detection.
        
        Args:
            text: The text to analyze.
            
        Returns:
            A JSON string with basic threat analysis.
        """
        logger.warning("Using fallback keyword analysis due to AI unavailability")
        
        # Define keyword categories
        keywords = {
            ThreatCategory.POLITICAL_UNREST: [
                "protest", "riot", "demonstration", "unrest", "coup", "revolution",
                "political crisis", "civil unrest", "uprising"
            ],
            ThreatCategory.TRANSPORT_DISRUPTION: [
                "delay", "cancel", "strike", "airport", "railway", "road block",
                "traffic", "transport", "travel warning", "border closed"
            ],
            ThreatCategory.WEATHER_EMERGENCY: [
                "storm", "flood", "hurricane", "tornado", "typhoon", "earthquake",
                "tsunami", "landslide", "wildfire", "extreme weather"
            ],
            ThreatCategory.SECURITY_INCIDENT: [
                "attack", "terrorism", "shooting", "explosion", "bomb", "hostage",
                "kidnap", "threat", "security alert", "evacuation"
            ],
            ThreatCategory.ECONOMIC_IMPACT: [
                "inflation", "recession", "currency", "economic crisis", "financial",
                "market crash", "bank", "shortage", "price increase", "devaluation"
            ],
            ThreatCategory.HEALTH_EMERGENCY: [
                "outbreak", "epidemic", "pandemic", "virus", "disease", "infection",
                "quarantine", "health alert", "medical", "hospital"
            ]
        }
        
        # Count keyword matches
        category_scores = {}
        text_lower = text.lower()
        
        for category, category_keywords in keywords.items():
            score = sum(1 for keyword in category_keywords if keyword in text_lower)
            category_scores[category.value] = score
        
        # Determine primary category
        primary_category = max(category_scores, key=category_scores.get)
        
        # Calculate severity based on keyword density
        total_matches = sum(category_scores.values())
        text_length = len(text.split())
        keyword_density = total_matches / max(1, text_length)
        severity = min(10, max(1, int(keyword_density * 100)))
        
        # Extract a summary (first 2-3 sentences)
        sentences = sent_tokenize(text)
        summary = " ".join(sentences[:min(3, len(sentences))])
        
        # Create fallback analysis
        analysis = {
            "title": summary[:100] + "..." if len(summary) > 100 else summary,
            "description": summary,
            "category": primary_category,
            "severity": severity,
            "confidence_score": 0.3,  # Low confidence for fallback
            "missionary_relevance": 50,  # Neutral relevance
            "status": ThreatStatus.MONITORING.value
        }
        
        return json.dumps(analysis)
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """
        Extract JSON from the model's response.
        
        Args:
            response: The model's response.
            
        Returns:
            Parsed JSON data.
        """
        try:
            # Try to find JSON block in the response
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find any JSON-like structure
                json_match = re.search(r'(\{.*\})', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = response
            
            # Parse JSON
            return json.loads(json_str)
        
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from response: {response}")
            # Return empty dict to avoid further errors
            return {}
    
    async def analyze_article(self, article_text: str, source_name: str, url: str) -> Dict[str, Any]:
        """
        Analyze an article for threats.
        
        Args:
            article_text: The article text to analyze.
            source_name: The name of the source.
            url: The URL of the article.
            
        Returns:
            Analysis results.
        """
        # Create prompt for threat analysis
        prompt = f"""
        You are an intelligence analyst for missionary operations. Analyze the following news article for potential threats to missionary safety and operations.
        
        Article from {source_name}:
        {article_text}
        
        Analyze this article and extract any potential threats to missionary operations. Return your analysis in JSON format with the following structure:
        ```json
        {{
            "title": "Brief title describing the threat",
            "description": "Concise description of the threat (2-3 sentences)",
            "category": "One of: political_unrest, transport_disruption, weather_emergency, security_incident, economic_impact, health_emergency",
            "severity": "Numeric rating from 1-10 where 10 is most severe",
            "confidence_score": "Confidence in this analysis from 0.0 to 1.0",
            "missionary_relevance": "Relevance to missionary operations from 0-100",
            "status": "One of: active, monitoring, resolved",
            "country": "Country where the threat is occurring",
            "city": "City or region where the threat is occurring (if mentioned)"
        }}
        ```
        
        If there is no significant threat to missionary operations in this article, return:
        ```json
        {{
            "title": "No significant threat detected",
            "description": "This article does not contain information about significant threats to missionary operations",
            "category": "security_incident",
            "severity": 1,
            "confidence_score": 0.9,
            "missionary_relevance": 10,
            "status": "resolved",
            "country": null,
            "city": null
        }}
        ```
        
        Only return the JSON. Do not include any other text in your response.
        """
        
        # Get AI response
        response = await self._make_ollama_request(prompt)
        
        # Extract JSON from response
        analysis = self._extract_json_from_response(response)
        
        # Add source information
        analysis["source_url"] = url
        analysis["source_name"] = source_name
        
        # Add processing timestamp
        analysis["processed_at"] = datetime.utcnow().isoformat()
        
        return analysis
    
    async def get_geolocation(self, country: str, city: Optional[str] = None) -> Tuple[Optional[float], Optional[float]]:
        """
        Get approximate geolocation for a country and city.
        
        Args:
            country: Country name.
            city: Optional city name.
            
        Returns:
            Tuple of (latitude, longitude) or (None, None) if not found.
        """
        # Create prompt for geolocation
        location = f"{city}, {country}" if city else country
        prompt = f"""
        Return the approximate latitude and longitude coordinates for {location}.
        
        Return only the coordinates in JSON format like this:
        ```json
        {{
            "latitude": 51.5074,
            "longitude": -0.1278
        }}
        ```
        
        If you cannot determine the coordinates, return:
        ```json
        {{
            "latitude": null,
            "longitude": null
        }}
        ```
        
        Only return the JSON. Do not include any other text in your response.
        """
        
        # Get AI response
        response = await self._make_ollama_request(prompt)
        
        # Extract JSON from response
        try:
            geo_data = self._extract_json_from_response(response)
            return geo_data.get("latitude"), geo_data.get("longitude")
        except Exception as e:
            logger.error(f"Failed to get geolocation for {location}: {e}")
            return None, None


# Create global instance
ai_processor = AIProcessor()
