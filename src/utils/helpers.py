"""
Helper utilities for WATCHKEEPER Testing Edition.

This module provides general utility functions.
"""

import re
import json
import uuid
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import hashlib
import unicodedata
import socket
from urllib.parse import urlparse

from src.core.logging import logger


def generate_id() -> str:
    """
    Generate a unique ID.
    
    Returns:
        Unique ID string.
    """
    return str(uuid.uuid4())


def slugify(text: str) -> str:
    """
    Convert text to a URL-friendly slug.
    
    Args:
        text: Text to slugify.
        
    Returns:
        Slugified text.
    """
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    
    # Remove non-word characters and replace spaces with hyphens
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[-\s]+', '-', text)
    
    return text


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate.
        max_length: Maximum length.
        suffix: Suffix to add if truncated.
        
    Returns:
        Truncated text.
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from text.
    
    Args:
        text: Text containing JSON.
        
    Returns:
        Extracted JSON or None if not found.
    """
    # Find JSON patterns in text
    json_pattern = r'(\{.*?\}|\[.*?\])'
    matches = re.findall(json_pattern, text, re.DOTALL)
    
    if not matches:
        return None
    
    # Try to parse each match
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    return None


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse a date string into a datetime object.
    
    Args:
        date_str: Date string to parse.
        
    Returns:
        Parsed datetime or None if parsing failed.
    """
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",  # ISO format with timezone
        "%Y-%m-%dT%H:%M:%S.%f%z",  # ISO format with microseconds and timezone
        "%Y-%m-%dT%H:%M:%S",  # ISO format without timezone
        "%Y-%m-%dT%H:%M:%S.%f",  # ISO format with microseconds
        "%Y-%m-%d %H:%M:%S",  # Simple format
        "%Y-%m-%d",  # Date only
        "%a, %d %b %Y %H:%M:%S %z",  # RSS format
        "%a, %d %b %Y %H:%M:%S",  # RSS format without timezone
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None


def format_date(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a datetime object as a string.
    
    Args:
        dt: Datetime to format.
        fmt: Format string.
        
    Returns:
        Formatted date string.
    """
    return dt.strftime(fmt)


def get_domain_from_url(url: str) -> str:
    """
    Extract domain from URL.
    
    Args:
        url: URL to extract domain from.
        
    Returns:
        Domain name.
    """
    parsed = urlparse(url)
    domain = parsed.netloc
    
    # Remove www. prefix if present
    if domain.startswith('www.'):
        domain = domain[4:]
    
    return domain


def is_url_accessible(url: str, timeout: int = 5) -> bool:
    """
    Check if a URL is accessible.
    
    Args:
        url: URL to check.
        timeout: Connection timeout in seconds.
        
    Returns:
        True if accessible, False otherwise.
    """
    try:
        parsed = urlparse(url)
        host = parsed.netloc
        
        # Try to establish a connection
        socket.create_connection((host, 80), timeout=timeout)
        return True
    except Exception:
        return False


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extract keywords from text using a simple approach.
    
    Args:
        text: Text to extract keywords from.
        max_keywords: Maximum number of keywords to extract.
        
    Returns:
        List of keywords.
    """
    # Normalize and clean text
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    
    # Split into words
    words = text.split()
    
    # Remove common stop words
    stop_words = {
        'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
        'which', 'this', 'that', 'these', 'those', 'then', 'just', 'so', 'than',
        'such', 'both', 'through', 'about', 'for', 'is', 'of', 'while', 'during',
        'to', 'from', 'in', 'on', 'by', 'with', 'at', 'be', 'was', 'were', 'will',
        'have', 'has', 'had', 'do', 'does', 'did', 'can', 'could', 'should', 'would',
        'may', 'might', 'must', 'shall', 'not', 'no', 'nor', 'yes', 'it', 'its',
        'they', 'them', 'their', 'he', 'him', 'his', 'she', 'her', 'hers', 'we',
        'us', 'our', 'you', 'your', 'yours', 'i', 'me', 'my', 'mine', 'said'
    }
    
    filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
    
    # Count word frequencies
    word_counts = {}
    for word in filtered_words:
        if word in word_counts:
            word_counts[word] += 1
        else:
            word_counts[word] = 1
    
    # Sort by frequency
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Return top keywords
    return [word for word, _ in sorted_words[:max_keywords]]


def calculate_text_hash(text: str) -> str:
    """
    Calculate a hash for text content.
    
    Args:
        text: Text to hash.
        
    Returns:
        Hash string.
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def format_bytes(size_bytes: int) -> str:
    """
    Format bytes as a human-readable string.
    
    Args:
        size_bytes: Size in bytes.
        
    Returns:
        Formatted size string.
    """
    if size_bytes == 0:
        return "0B"
    
    size_names = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.2f}{size_names[i]}"
