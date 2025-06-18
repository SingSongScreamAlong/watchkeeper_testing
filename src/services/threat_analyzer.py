"""
Threat analyzer service for WATCHKEEPER Testing Edition.

This module provides threat classification and analysis logic.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.logging import logger
from src.core.database import SessionLocal
from src.models.threat import Threat, ThreatCategory, ThreatStatus
from src.services.ai_processor import ai_processor


class ThreatAnalyzer:
    """
    Threat analyzer for WATCHKEEPER Testing Edition.
    
    Provides threat classification, clustering, and trend analysis.
    """
    
    def __init__(self):
        """Initialize the threat analyzer."""
        pass
    
    async def classify_threat(self, threat_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify a threat based on its data.
        
        Args:
            threat_data: Threat data to classify.
            
        Returns:
            Classified threat data.
        """
        # Extract text for analysis
        text = f"{threat_data.get('title', '')}\n{threat_data.get('description', '')}"
        
        # Determine severity if not provided
        if "severity" not in threat_data or threat_data["severity"] is None:
            # Simple keyword-based severity assessment
            severity_keywords = {
                9: ["critical", "imminent", "extreme danger", "evacuation", "mass casualty"],
                7: ["danger", "violent", "armed", "explosion", "attack", "killed"],
                5: ["warning", "alert", "protest", "demonstration", "disruption"],
                3: ["concern", "monitor", "potential", "possible", "reported"]
            }
            
            text_lower = text.lower()
            severity = 1  # Default
            
            for level, keywords in severity_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    severity = level
                    break
                    
            threat_data["severity"] = severity
        
        # Determine category if not provided
        if "category" not in threat_data or threat_data["category"] is None:
            # Simple keyword-based category assessment
            category_keywords = {
                ThreatCategory.POLITICAL_UNREST: [
                    "protest", "riot", "demonstration", "election", "political", "government",
                    "coup", "unrest", "uprising"
                ],
                ThreatCategory.TRANSPORT_DISRUPTION: [
                    "airport", "flight", "train", "road", "traffic", "delay", "cancel",
                    "transport", "travel", "border"
                ],
                ThreatCategory.WEATHER_EMERGENCY: [
                    "storm", "flood", "hurricane", "tornado", "typhoon", "earthquake",
                    "tsunami", "weather", "rain", "snow", "temperature"
                ],
                ThreatCategory.SECURITY_INCIDENT: [
                    "attack", "terrorism", "shooting", "explosion", "bomb", "hostage",
                    "kidnap", "security", "police", "military", "weapon"
                ],
                ThreatCategory.ECONOMIC_IMPACT: [
                    "economy", "financial", "currency", "inflation", "market", "stock",
                    "bank", "price", "cost", "shortage", "supply"
                ],
                ThreatCategory.HEALTH_EMERGENCY: [
                    "disease", "virus", "outbreak", "infection", "hospital", "medical",
                    "health", "patient", "doctor", "treatment", "vaccine"
                ]
            }
            
            text_lower = text.lower()
            category = ThreatCategory.SECURITY_INCIDENT  # Default
            max_matches = 0
            
            for cat, keywords in category_keywords.items():
                matches = sum(1 for keyword in keywords if keyword in text_lower)
                if matches > max_matches:
                    max_matches = matches
                    category = cat
                    
            threat_data["category"] = category.value
        
        # Determine missionary relevance if not provided
        if "missionary_relevance" not in threat_data or threat_data["missionary_relevance"] is None:
            # Base relevance on severity and keywords
            relevance_keywords = [
                "church", "missionary", "religious", "christian", "faith", "worship",
                "foreigner", "westerner", "american", "european", "international",
                "evacuation", "embassy", "consulate", "visa", "passport", "travel advisory"
            ]
            
            text_lower = text.lower()
            keyword_matches = sum(1 for keyword in relevance_keywords if keyword in text_lower)
            base_relevance = min(100, keyword_matches * 10)
            
            # Adjust based on severity
            severity_factor = threat_data.get("severity", 5) * 5
            
            # Calculate final relevance
            relevance = min(100, max(10, (base_relevance + severity_factor) / 2))
            threat_data["missionary_relevance"] = int(relevance)
        
        return threat_data
    
    async def get_related_threats(self, threat_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get threats related to a specific threat.
        
        Args:
            threat_id: ID of the threat to find related threats for.
            limit: Maximum number of related threats to return.
            
        Returns:
            List of related threats.
        """
        with SessionLocal() as db:
            # Get the target threat
            threat = db.query(Threat).filter(Threat.id == threat_id).first()
            
            if not threat:
                logger.warning(f"Threat not found: {threat_id}")
                return []
            
            # Find threats in the same category and country
            related = db.query(Threat).filter(
                Threat.id != threat_id,
                Threat.category == threat.category,
                Threat.country == threat.country if threat.country else True,
                Threat.is_active == True
            ).order_by(desc(Threat.created_at)).limit(limit).all()
            
            return [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "severity": t.severity,
                    "category": t.category.value,
                    "country": t.country,
                    "city": t.city,
                    "created_at": t.created_at.isoformat()
                }
                for t in related
            ]
    
    async def get_threat_trends(self, days: int = 30) -> Dict[str, Any]:
        """
        Get threat trends over time.
        
        Args:
            days: Number of days to analyze.
            
        Returns:
            Threat trend data.
        """
        with SessionLocal() as db:
            # Calculate date cutoff
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get daily threat counts
            daily_counts = []
            current_date = cutoff_date
            end_date = datetime.utcnow()
            
            while current_date <= end_date:
                next_date = current_date + timedelta(days=1)
                
                count = db.query(func.count(Threat.id)).filter(
                    Threat.created_at >= current_date,
                    Threat.created_at < next_date
                ).scalar()
                
                daily_counts.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "count": count
                })
                
                current_date = next_date
            
            # Get category distribution
            category_counts = {}
            for category in ThreatCategory:
                count = db.query(func.count(Threat.id)).filter(
                    Threat.category == category,
                    Threat.created_at >= cutoff_date
                ).scalar()
                category_counts[category.value] = count
            
            # Get severity distribution
            severity_counts = {i: 0 for i in range(1, 11)}
            for severity in range(1, 11):
                count = db.query(func.count(Threat.id)).filter(
                    Threat.severity == severity,
                    Threat.created_at >= cutoff_date
                ).scalar()
                severity_counts[severity] = count
            
            # Get top countries
            country_query = db.query(
                Threat.country,
                func.count(Threat.id).label("count")
            ).filter(
                Threat.created_at >= cutoff_date,
                Threat.country.isnot(None)
            ).group_by(Threat.country).order_by(desc("count")).limit(5)
            
            country_counts = {row.country: row.count for row in country_query}
            
            return {
                "daily_counts": daily_counts,
                "category_distribution": category_counts,
                "severity_distribution": severity_counts,
                "country_distribution": country_counts,
                "total_threats": sum(c["count"] for c in daily_counts),
                "days_analyzed": days
            }
    
    async def update_threat_statuses(self) -> Dict[str, Any]:
        """
        Update threat statuses based on age and other factors.
        
        Returns:
            Status update statistics.
        """
        with SessionLocal() as db:
            # Find active threats older than 7 days
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            old_threats = db.query(Threat).filter(
                Threat.status == ThreatStatus.ACTIVE,
                Threat.created_at < cutoff_date
            ).all()
            
            # Update to monitoring status
            monitoring_count = 0
            for threat in old_threats:
                threat.status = ThreatStatus.MONITORING
                monitoring_count += 1
            
            # Find monitoring threats older than 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            old_monitoring = db.query(Threat).filter(
                Threat.status == ThreatStatus.MONITORING,
                Threat.created_at < cutoff_date
            ).all()
            
            # Update to resolved status
            resolved_count = 0
            for threat in old_monitoring:
                threat.status = ThreatStatus.RESOLVED
                resolved_count += 1
            
            # Commit changes
            db.commit()
            
            return {
                "updated_to_monitoring": monitoring_count,
                "updated_to_resolved": resolved_count,
                "total_updated": monitoring_count + resolved_count
            }


# Create global instance
threat_analyzer = ThreatAnalyzer()
