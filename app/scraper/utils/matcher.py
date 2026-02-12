"""Keyword matching utilities for job filtering."""

import re
from typing import Any, Dict, List, Optional


class KeywordMatcher:
    """Matches job postings against keyword groups with smart boundary detection."""
    
    def __init__(self, keyword_groups: Dict[str, List[str]], match_rules: Dict[str, Any]):
        """Initialize matcher with config dicts.
        
        Args:
            keyword_groups: Dict mapping group names to lists of keywords
            match_rules: Dict with match rules (e.g., skip_location_for)
        """
        self.keyword_groups = keyword_groups
        self.match_rules = match_rules
        self.skip_location_for = set(self.match_rules.get('skip_location_for', []))
        
        # Precompile regex patterns for efficiency
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for each keyword with smart boundary detection."""
        self.patterns = {}
        
        for group_name, keywords in self.keyword_groups.items():
            self.patterns[group_name] = []
            
            for keyword in keywords:
                # Check if keyword contains CJK characters
                has_cjk = bool(re.search(r'[\u4e00-\u9fff]', keyword))
                
                if has_cjk:
                    # CJK keywords: use substring match (escape special chars)
                    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                else:
                    # English keywords: use word boundary for short alphanumeric-only ones (<=3 chars)
                    # Only use \b for keywords that are purely alphanumeric (no special chars)
                    is_alphanumeric = keyword.replace(' ', '').isalnum()
                    if len(keyword) <= 3 and is_alphanumeric:
                        # Short alphanumeric keywords like "AI", "NLP", "RAG", "GPT", "LLM", "wfh"
                        pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                    else:
                        # Longer keywords or keywords with special chars: substring match
                        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                
                self.patterns[group_name].append(pattern)
    
    def match_group(self, text: str, group_name: str) -> bool:
        """Check if text matches any keyword in the group (OR logic).
        
        Args:
            text: Text to search in
            group_name: Name of keyword group (e.g., 'location', 'technology')
        
        Returns:
            True if ANY keyword in the group matches the text
        """
        if not text or group_name not in self.patterns:
            return False
        
        # OR logic: any keyword match returns True
        for pattern in self.patterns[group_name]:
            if pattern.search(text):
                return True
        
        return False
    
    def match_job(self, job: dict, source: str) -> bool:
        """Check if job matches all required keyword groups (AND logic).
        
        Args:
            job: Job dict with 'title', 'description', 'tags' keys
            source: Source name (e.g., 'remoteok', 'weworkremotely')
        
        Returns:
            True if job matches all required groups
        """
        # Combine all job text fields
        text_parts = [
            job.get('title', ''),
            job.get('description', ''),
        ]
        
        # Add tags if present (could be list or string)
        tags = job.get('tags', '')
        if isinstance(tags, list):
            text_parts.extend(tags)
        elif tags:
            text_parts.append(tags)
        
        combined_text = ' '.join(str(part) for part in text_parts if part)
        
        if not combined_text:
            return False
        
        # Check technology group (always required)
        if not self.match_group(combined_text, 'technology'):
            return False
        
        # Check location group (skip for certain sources)
        if source not in self.skip_location_for:
            if not self.match_group(combined_text, 'location'):
                return False
        
        return True
