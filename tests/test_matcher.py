"""Comprehensive tests for keyword matcher."""

import pytest
from scraper.utils.matcher import KeywordMatcher


@pytest.fixture
def matcher():
    """Create matcher instance with default config."""
    return KeywordMatcher()


@pytest.fixture
def sample_config():
    """Sample config for testing."""
    return {
        'keyword_groups': {
            'location': ['remote', '远程', 'wfh'],
            'technology': ['AI', 'LLM', '大模型', 'machine learning']
        },
        'match_rules': {
            'default': 'location AND technology',
            'skip_location_for': ['remoteok', 'weworkremotely']
        }
    }


class TestKeywordMatcher:
    """Test KeywordMatcher class."""
    
    def test_init_with_default_path(self, matcher):
        """Test initialization with default config path."""
        assert 'location' in matcher.keyword_groups
        assert 'technology' in matcher.keyword_groups
        assert 'remoteok' in matcher.skip_location_for
        assert 'weworkremotely' in matcher.skip_location_for
    
    def test_init_with_config_dict(self, sample_config):
        """Test initialization with config dict."""
        matcher = KeywordMatcher(config=sample_config)
        assert matcher.keyword_groups == sample_config['keyword_groups']
        assert 'remoteok' in matcher.skip_location_for


class TestMatchGroup:
    """Test match_group() method."""
    
    def test_english_short_keyword_exact_match(self, matcher):
        """Test short English keyword with word boundary (AI)."""
        assert matcher.match_group("Senior AI Engineer", "technology") is True
        assert matcher.match_group("AI应用开发工程师", "technology") is True
        assert matcher.match_group("Looking for AI talent", "technology") is True
    
    def test_english_short_keyword_no_false_positive(self, matcher):
        """Test short English keyword doesn't match within words."""
        # "AI" should NOT match in "email", "wait", "train", etc.
        assert matcher.match_group("email marketing specialist", "technology") is False
        assert matcher.match_group("waiting room attendant", "technology") is False
        assert matcher.match_group("train conductor", "technology") is False
        assert matcher.match_group("daily operations manager", "technology") is False
    
    def test_english_short_keyword_case_insensitive(self, matcher):
        """Test short English keywords are case-insensitive."""
        assert matcher.match_group("ai engineer", "technology") is True
        assert matcher.match_group("AI ENGINEER", "technology") is True
        assert matcher.match_group("Ai Engineer", "technology") is True
        assert matcher.match_group("llm developer", "technology") is True
        assert matcher.match_group("NLP specialist", "technology") is True
    
    def test_english_longer_keyword(self, matcher):
        """Test longer English keywords use substring match."""
        assert matcher.match_group("machine learning engineer", "technology") is True
        assert matcher.match_group("deep learning specialist", "technology") is True
        assert matcher.match_group("artificial intelligence researcher", "technology") is True
    
    def test_chinese_keyword_substring_match(self, matcher):
        """Test Chinese keywords use substring match."""
        assert matcher.match_group("AI应用开发工程师", "technology") is True
        assert matcher.match_group("大模型应用开发", "technology") is True
        assert matcher.match_group("机器学习工程师", "technology") is True
        assert matcher.match_group("自然语言处理专家", "technology") is True
    
    def test_chinese_location_keywords(self, matcher):
        """Test Chinese location keywords."""
        assert matcher.match_group("远程工作", "location") is True
        assert matcher.match_group("支持远程办公", "location") is True
        assert matcher.match_group("在家办公", "location") is True
    
    def test_mixed_chinese_english(self, matcher):
        """Test mixed Chinese and English text."""
        assert matcher.match_group("远程 LLM 应用开发", "technology") is True
        assert matcher.match_group("Remote AI 工程师", "location") is True
    
    def test_or_logic_within_group(self, matcher):
        """Test OR logic: any keyword match returns True."""
        # Multiple tech keywords
        assert matcher.match_group("GPT-4 integration", "technology") is True
        assert matcher.match_group("Claude API developer", "technology") is True
        assert matcher.match_group("RAG system architect", "technology") is True
        
        # Multiple location keywords
        assert matcher.match_group("fully remote position", "location") is True
        assert matcher.match_group("work from home", "location") is True
        assert matcher.match_group("location independent", "location") is True
    
    def test_empty_text(self, matcher):
        """Test empty text returns False."""
        assert matcher.match_group("", "technology") is False
        assert matcher.match_group("", "location") is False
        assert matcher.match_group(None, "technology") is False
    
    def test_invalid_group_name(self, matcher):
        """Test invalid group name returns False."""
        assert matcher.match_group("AI Engineer", "invalid_group") is False
    
    def test_no_match(self, matcher):
        """Test text with no matching keywords."""
        assert matcher.match_group("accountant position", "technology") is False
        assert matcher.match_group("on-site only", "location") is False


class TestMatchJob:
    """Test match_job() method."""
    
    def test_job_with_tech_and_location(self, matcher):
        """Test job matching both technology and location."""
        job = {
            'title': 'Senior AI Engineer - Remote',
            'description': 'Build LLM applications',
            'tags': ['python', 'machine learning']
        }
        assert matcher.match_job(job, 'linkedin') is True
    
    def test_job_tech_only_no_location(self, matcher):
        """Test job with tech but no location (should fail for normal sources)."""
        job = {
            'title': 'AI Engineer',
            'description': 'Build machine learning models',
            'tags': []
        }
        assert matcher.match_job(job, 'linkedin') is False
    
    def test_job_location_only_no_tech(self, matcher):
        """Test job with location but no tech (should fail)."""
        job = {
            'title': 'Remote Accountant',
            'description': 'Work from home position',
            'tags': []
        }
        assert matcher.match_job(job, 'linkedin') is False
    
    def test_job_skip_location_for_remoteok(self, matcher):
        """Test location check skipped for remoteok source."""
        job = {
            'title': 'AI Engineer',
            'description': 'Build LLM applications',
            'tags': []
        }
        # Should pass for remoteok (location not required)
        assert matcher.match_job(job, 'remoteok') is True
        # Should fail for other sources (location required)
        assert matcher.match_job(job, 'linkedin') is False
    
    def test_job_skip_location_for_weworkremotely(self, matcher):
        """Test location check skipped for weworkremotely source."""
        job = {
            'title': 'Machine Learning Engineer',
            'description': 'Deep learning projects',
            'tags': []
        }
        assert matcher.match_job(job, 'weworkremotely') is True
        assert matcher.match_job(job, 'indeed') is False
    
    def test_job_chinese_content(self, matcher):
        """Test job with Chinese content."""
        job = {
            'title': 'AI应用开发工程师',
            'description': '负责大模型应用开发，支持远程工作',
            'tags': ['Python', 'LLM']
        }
        assert matcher.match_job(job, 'zhipin') is True
    
    def test_job_mixed_chinese_english(self, matcher):
        """Test job with mixed Chinese and English."""
        job = {
            'title': '远程 LLM 应用开发',
            'description': 'Build AI applications with GPT-4',
            'tags': []
        }
        assert matcher.match_job(job, 'linkedin') is True
    
    def test_job_false_positive_prevention(self, matcher):
        """Test that false positives are prevented."""
        # "AI" in "email" should not match
        job = {
            'title': 'Email Marketing Specialist - Remote',
            'description': 'Manage email campaigns',
            'tags': []
        }
        assert matcher.match_job(job, 'linkedin') is False
        
        # "AI" in "waiting" should not match
        job = {
            'title': 'Remote Customer Service - Waiting Room',
            'description': 'Handle customer inquiries',
            'tags': []
        }
        assert matcher.match_job(job, 'linkedin') is False
    
    def test_job_tags_as_list(self, matcher):
        """Test job with tags as list."""
        job = {
            'title': 'Engineer',
            'description': 'Build applications',
            'tags': ['AI', 'remote', 'python']
        }
        assert matcher.match_job(job, 'linkedin') is True
    
    def test_job_tags_as_string(self, matcher):
        """Test job with tags as string."""
        job = {
            'title': 'Engineer',
            'description': 'Build applications',
            'tags': 'AI, remote, python'
        }
        assert matcher.match_job(job, 'linkedin') is True
    
    def test_job_empty_fields(self, matcher):
        """Test job with empty fields."""
        job = {
            'title': '',
            'description': '',
            'tags': []
        }
        assert matcher.match_job(job, 'linkedin') is False
    
    def test_job_missing_fields(self, matcher):
        """Test job with missing fields."""
        job = {}
        assert matcher.match_job(job, 'linkedin') is False
        
        job = {'title': 'AI Engineer Remote'}
        assert matcher.match_job(job, 'linkedin') is True
    
    def test_job_all_keywords_in_title(self, matcher):
        """Test job with all keywords in title only."""
        job = {
            'title': 'Remote AI Engineer - LLM Development',
            'description': '',
            'tags': []
        }
        assert matcher.match_job(job, 'linkedin') is True
    
    def test_job_all_keywords_in_description(self, matcher):
        """Test job with all keywords in description only."""
        job = {
            'title': 'Software Engineer',
            'description': 'Remote position building AI and machine learning systems',
            'tags': []
        }
        assert matcher.match_job(job, 'linkedin') is True
    
    def test_job_keywords_split_across_fields(self, matcher):
        """Test job with keywords split across different fields."""
        job = {
            'title': 'Software Engineer',
            'description': 'Build machine learning models',
            'tags': ['remote', 'AI']
        }
        assert matcher.match_job(job, 'linkedin') is True


class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_special_characters_in_keywords(self, sample_config):
        """Test keywords with special regex characters."""
        config = {
            'keyword_groups': {
                'location': ['remote'],
                'technology': ['C++', '.NET', 'AI/ML']
            },
            'match_rules': {
                'skip_location_for': []
            }
        }
        matcher = KeywordMatcher(config=config)
        
        job = {
            'title': 'Remote C++ Developer',
            'description': 'Build high-performance systems',
            'tags': []
        }
        assert matcher.match_job(job, 'linkedin') is True
    
    def test_multiple_short_keywords(self, matcher):
        """Test multiple short keywords in same text."""
        text = "AI and NLP engineer with LLM experience"
        assert matcher.match_group(text, "technology") is True
        
        # Verify each keyword individually
        assert matcher.match_group("AI engineer", "technology") is True
        assert matcher.match_group("NLP specialist", "technology") is True
        assert matcher.match_group("LLM developer", "technology") is True
    
    def test_keyword_at_boundaries(self, matcher):
        """Test keywords at text boundaries."""
        assert matcher.match_group("AI", "technology") is True
        assert matcher.match_group("AI.", "technology") is True
        assert matcher.match_group("(AI)", "technology") is True
        assert matcher.match_group("AI,", "technology") is True
        assert matcher.match_group("AI!", "technology") is True
    
    def test_case_variations(self, matcher):
        """Test various case combinations."""
        variations = [
            "ai engineer",
            "AI engineer", 
            "Ai engineer",
            "aI engineer",
            "AI ENGINEER",
            "ai ENGINEER"
        ]
        for text in variations:
            assert matcher.match_group(text, "technology") is True
