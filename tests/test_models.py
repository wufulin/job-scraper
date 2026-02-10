"""Tests for scraper.models module."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from scraper.models import VALID_SOURCES, JobPosting, _load_valid_sources


class TestJobPostingToPgDict:
    """Test to_pg_dict() method for PostgreSQL serialization."""

    def test_to_pg_dict_returns_timezone_aware_datetimes(self):
        """to_pg_dict() should return timezone-aware datetime objects, not ISO strings."""
        now_utc = datetime.now(timezone.utc)
        job = JobPosting(
            id="test-id",
            title="Test Job",
            company="Test Corp",
            url="https://example.com/job",
            source="remoteok",
            first_seen=now_utc,
            last_seen=now_utc,
            last_updated=now_utc,
        )
        
        result = job.to_pg_dict()
        
        # Datetimes should be datetime objects, not strings
        assert isinstance(result["first_seen"], datetime)
        assert isinstance(result["last_seen"], datetime)
        assert isinstance(result["last_updated"], datetime)
        
        # Should be timezone-aware
        assert result["first_seen"].tzinfo is not None
        assert result["last_seen"].tzinfo is not None
        assert result["last_updated"].tzinfo is not None

    def test_to_pg_dict_returns_list_for_tags(self):
        """to_pg_dict() should return list[str] for tags, not JSON string."""
        job = JobPosting(
            id="test-id",
            title="Test Job",
            url="https://example.com/job",
            source="remoteok",
            tags=["python", "remote", "ai"],
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
        )
        
        result = job.to_pg_dict()
        
        # Tags should be a list, not JSON string
        assert isinstance(result["tags"], list)
        assert result["tags"] == ["python", "remote", "ai"]

    def test_to_pg_dict_all_fields_present(self):
        """to_pg_dict() should include all fields."""
        now_utc = datetime.now(timezone.utc)
        pub_date = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        job = JobPosting(
            id="test-id",
            title="Test Job",
            company="Test Corp",
            url="https://example.com/job",
            source="remoteok",
            published_at=pub_date,
            salary="$100k-$150k",
            location="Remote",
            description="Test description",
            tags=["python"],
            first_seen=now_utc,
            last_seen=now_utc,
            last_updated=now_utc,
            update_count=2,
        )
        
        result = job.to_pg_dict()
        
        assert result["id"] == "test-id"
        assert result["title"] == "Test Job"
        assert result["company"] == "Test Corp"
        assert result["url"] == "https://example.com/job"
        assert result["source"] == "remoteok"
        assert result["published_at"] == pub_date
        assert result["salary"] == "$100k-$150k"
        assert result["location"] == "Remote"
        assert result["description"] == "Test description"
        assert result["tags"] == ["python"]
        assert result["update_count"] == 2

    def test_to_pg_dict_handles_none_values(self):
        """to_pg_dict() should preserve None values."""
        job = JobPosting(
            id="test-id",
            title="Test Job",
            url="https://example.com/job",
            source="remoteok",
            company=None,
            published_at=None,
            salary=None,
            location=None,
            description=None,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
        )
        
        result = job.to_pg_dict()
        
        assert result["company"] is None
        assert result["published_at"] is None
        assert result["salary"] is None
        assert result["location"] is None
        assert result["description"] is None


class TestJobPostingFromPgRow:
    """Test from_pg_row() class method for PostgreSQL deserialization."""

    def test_from_pg_row_deserializes_timezone_aware_datetimes(self):
        """from_pg_row() should accept timezone-aware datetime objects."""
        now_utc = datetime.now(timezone.utc)
        
        # Mock asyncpg.Record
        row = MagicMock()
        row.__getitem__ = lambda self, key: {
            "id": "test-id",
            "title": "Test Job",
            "company": "Test Corp",
            "url": "https://example.com/job",
            "source": "remoteok",
            "published_at": now_utc,
            "salary": "$100k",
            "location": "Remote",
            "description": "Test desc",
            "tags": ["python", "remote"],
            "first_seen": now_utc,
            "last_seen": now_utc,
            "last_updated": now_utc,
            "update_count": 1,
        }[key]
        
        job = JobPosting.from_pg_row(row)
        
        assert job.id == "test-id"
        assert job.title == "Test Job"
        assert job.company == "Test Corp"
        assert job.url == "https://example.com/job"
        assert job.source == "remoteok"
        assert job.published_at == now_utc
        assert job.salary == "$100k"
        assert job.location == "Remote"
        assert job.description == "Test desc"
        assert job.tags == ["python", "remote"]
        assert job.first_seen == now_utc
        assert job.last_seen == now_utc
        assert job.last_updated == now_utc
        assert job.update_count == 1

    def test_from_pg_row_handles_none_values(self):
        """from_pg_row() should handle None values correctly."""
        now_utc = datetime.now(timezone.utc)
        
        row = MagicMock()
        row.__getitem__ = lambda self, key: {
            "id": "test-id",
            "title": "Test Job",
            "company": None,
            "url": "https://example.com/job",
            "source": "remoteok",
            "published_at": None,
            "salary": None,
            "location": None,
            "description": None,
            "tags": [],
            "first_seen": now_utc,
            "last_seen": now_utc,
            "last_updated": now_utc,
            "update_count": 1,
        }[key]
        
        job = JobPosting.from_pg_row(row)
        
        assert job.company is None
        assert job.published_at is None
        assert job.salary is None
        assert job.location is None
        assert job.description is None
        assert job.tags == []

    def test_from_pg_row_roundtrip_with_to_pg_dict(self):
        """from_pg_row() should correctly deserialize output from to_pg_dict()."""
        now_utc = datetime.now(timezone.utc)
        original = JobPosting(
            id="test-id",
            title="Test Job",
            company="Test Corp",
            url="https://example.com/job",
            source="remoteok",
            published_at=now_utc,
            salary="$100k",
            location="Remote",
            description="Test desc",
            tags=["python", "remote"],
            first_seen=now_utc,
            last_seen=now_utc,
            last_updated=now_utc,
            update_count=2,
        )
        
        # Serialize to pg dict
        pg_dict = original.to_pg_dict()
        
        # Mock asyncpg.Record from pg_dict
        row = MagicMock()
        row.__getitem__ = lambda self, key: pg_dict[key]
        
        # Deserialize back
        restored = JobPosting.from_pg_row(row)
        
        # Should match original
        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.company == original.company
        assert restored.url == original.url
        assert restored.source == original.source
        assert restored.published_at == original.published_at
        assert restored.salary == original.salary
        assert restored.location == original.location
        assert restored.description == original.description
        assert restored.tags == original.tags
        assert restored.first_seen == original.first_seen
        assert restored.last_seen == original.last_seen
        assert restored.last_updated == original.last_updated
        assert restored.update_count == original.update_count


class TestJobPostingDatetimeDefaults:
    """Test that datetime fields use timezone-aware defaults."""

    def test_datetime_fields_are_timezone_aware(self):
        """When creating JobPosting with datetime.now(timezone.utc), fields should be timezone-aware."""
        now_utc = datetime.now(timezone.utc)
        job = JobPosting(
            id="test-id",
            title="Test Job",
            url="https://example.com/job",
            source="remoteok",
            first_seen=now_utc,
            last_seen=now_utc,
            last_updated=now_utc,
        )
        
        assert job.first_seen.tzinfo is not None
        assert job.last_seen.tzinfo is not None
        assert job.last_updated.tzinfo is not None


class TestValidSources:
    """Test VALID_SOURCES dynamic loading."""

    def test_valid_sources_is_set(self):
        """VALID_SOURCES should be a set."""
        assert isinstance(VALID_SOURCES, set)

    def test_valid_sources_contains_expected_sources(self):
        """VALID_SOURCES should contain all Phase 1 + Phase 2 sources."""
        expected = {"remoteok", "eleduck", "weworkremotely", "workgo", "v2ex", "arcdev", "yuancheng"}
        assert VALID_SOURCES == expected

    def test_load_valid_sources_returns_set(self):
        """_load_valid_sources() should return a set."""
        sources = _load_valid_sources()
        assert isinstance(sources, set)

    def test_load_valid_sources_fallback_when_db_unavailable(self):
        """_load_valid_sources() should fallback to hardcoded set if DB unavailable."""
        # This test verifies the fallback works (DB may not be available in test env)
        sources = _load_valid_sources()
        expected = {"remoteok", "eleduck", "weworkremotely", "workgo", "v2ex", "arcdev", "yuancheng"}
        assert sources == expected

    def test_source_validator_uses_valid_sources(self):
        """JobPosting source validator should use VALID_SOURCES."""
        # Valid source should work
        job = JobPosting(
            id="test-id",
            title="Test Job",
            url="https://example.com/job",
            source="remoteok",
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
        )
        assert job.source == "remoteok"
        
        # Invalid source should raise
        with pytest.raises(ValueError, match="Source must be one of"):
            JobPosting(
                id="test-id",
                title="Test Job",
                url="https://example.com/job",
                source="invalid_source",
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
            )


class TestBackwardCompatibility:
    """Test that existing to_db_dict() and from_db_row() still work."""

    def test_to_db_dict_still_works(self):
        """to_db_dict() should still work for SQLite compatibility."""
        now_utc = datetime.now(timezone.utc)
        job = JobPosting(
            id="test-id",
            title="Test Job",
            url="https://example.com/job",
            source="remoteok",
            tags=["python"],
            first_seen=now_utc,
            last_seen=now_utc,
            last_updated=now_utc,
        )
        
        result = job.to_db_dict()
        
        # Should return ISO strings for datetimes
        assert isinstance(result["first_seen"], str)
        assert isinstance(result["last_seen"], str)
        assert isinstance(result["last_updated"], str)
        
        # Should return JSON string for tags
        assert isinstance(result["tags"], str)
        assert json.loads(result["tags"]) == ["python"]

    def test_from_db_row_still_works(self):
        """from_db_row() should still work for SQLite compatibility."""
        now_utc = datetime.now(timezone.utc)
        row = {
            "id": "test-id",
            "title": "Test Job",
            "company": "Test Corp",
            "url": "https://example.com/job",
            "source": "remoteok",
            "published_at": now_utc.isoformat(),
            "salary": "$100k",
            "location": "Remote",
            "description": "Test desc",
            "tags": json.dumps(["python"]),
            "first_seen": now_utc.isoformat(),
            "last_seen": now_utc.isoformat(),
            "last_updated": now_utc.isoformat(),
            "update_count": 1,
        }
        
        job = JobPosting.from_db_row(row)
        
        assert job.id == "test-id"
        assert job.title == "Test Job"
        assert job.tags == ["python"]
