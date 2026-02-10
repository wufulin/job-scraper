"""Tests for cross-site deduplication utility."""

from __future__ import annotations

from datetime import datetime

import pytest

from scraper.models import JobPosting
from scraper.utils.dedup import DedupManager, SIMILARITY_THRESHOLD


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_job(
    title: str = "AI Engineer",
    company: str | None = "Acme Inc",
    source: str = "remoteok",
    url: str = "https://example.com/job1",
    first_seen: datetime | None = None,
    last_seen: datetime | None = None,
    tags: list[str] | None = None,
) -> JobPosting:
    """Create a JobPosting for testing."""
    now = datetime(2025, 1, 15, 12, 0, 0)
    fs = first_seen or now
    ls = last_seen or now
    return JobPosting(
        id=JobPosting.generate_id(url, title),
        title=title,
        company=company,
        url=url,
        source=source,
        first_seen=fs,
        last_seen=ls,
        last_updated=ls,
        tags=tags or [],
    )


# ===========================================================================
# normalize_company
# ===========================================================================

class TestNormalizeCompany:
    """Tests for DedupManager.normalize_company."""

    def test_lowercase(self):
        assert DedupManager.normalize_company("ACME") == "acme"

    def test_strip_inc(self):
        assert DedupManager.normalize_company("Acme Inc") == "acme"

    def test_strip_inc_dot(self):
        assert DedupManager.normalize_company("Acme Inc.") == "acme"

    def test_strip_ltd(self):
        assert DedupManager.normalize_company("Acme Ltd") == "acme"

    def test_strip_llc(self):
        assert DedupManager.normalize_company("Acme LLC") == "acme"

    def test_strip_corp(self):
        assert DedupManager.normalize_company("Acme Corp") == "acme"

    def test_strip_gmbh(self):
        assert DedupManager.normalize_company("Siemens GmbH") == "siemens"

    def test_strip_limited(self):
        assert DedupManager.normalize_company("Acme Limited") == "acme"

    def test_strip_incorporated(self):
        assert DedupManager.normalize_company("Acme Incorporated") == "acme"

    def test_none_returns_empty(self):
        assert DedupManager.normalize_company(None) == ""

    def test_empty_returns_empty(self):
        assert DedupManager.normalize_company("") == ""

    def test_whitespace_collapse(self):
        assert DedupManager.normalize_company("  Acme   Inc  ") == "acme"

    def test_preserves_meaningful_words(self):
        assert DedupManager.normalize_company("Open AI Inc") == "open ai"


# ===========================================================================
# normalize_title
# ===========================================================================

class TestNormalizeTitle:
    """Tests for DedupManager.normalize_title."""

    def test_lowercase(self):
        assert DedupManager.normalize_title("AI Engineer") == "ai engineer"

    def test_strip_senior(self):
        assert DedupManager.normalize_title("Senior AI Engineer") == "ai engineer"

    def test_strip_junior(self):
        assert DedupManager.normalize_title("Junior AI Engineer") == "ai engineer"

    def test_strip_lead(self):
        assert DedupManager.normalize_title("Lead AI Engineer") == "ai engineer"

    def test_strip_staff(self):
        assert DedupManager.normalize_title("Staff AI Engineer") == "ai engineer"

    def test_strip_principal(self):
        assert DedupManager.normalize_title("Principal AI Engineer") == "ai engineer"

    def test_strip_intern(self):
        assert DedupManager.normalize_title("AI Engineer Intern") == "ai engineer"

    def test_strip_sr(self):
        assert DedupManager.normalize_title("Sr. AI Engineer") == "ai engineer"

    def test_strip_jr(self):
        assert DedupManager.normalize_title("Jr AI Engineer") == "ai engineer"

    def test_whitespace_collapse(self):
        assert DedupManager.normalize_title("  Senior  AI   Engineer  ") == "ai engineer"


# ===========================================================================
# similarity
# ===========================================================================

class TestSimilarity:
    """Tests for DedupManager.similarity."""

    def test_identical_strings(self):
        assert DedupManager.similarity("hello", "hello") == 1.0

    def test_empty_string_returns_zero(self):
        assert DedupManager.similarity("", "hello") == 0.0
        assert DedupManager.similarity("hello", "") == 0.0

    def test_completely_different(self):
        assert DedupManager.similarity("abc", "xyz") < 0.5

    def test_similar_strings(self):
        score = DedupManager.similarity("machine learning engineer", "machine learning eng")
        assert score > 0.8

    def test_above_threshold(self):
        score = DedupManager.similarity("ai engineer", "ai enginee")
        assert score > SIMILARITY_THRESHOLD


# ===========================================================================
# is_duplicate
# ===========================================================================

class TestIsDuplicate:
    """Tests for DedupManager.is_duplicate."""

    def test_cross_source_exact_match(self):
        a = _make_job(source="remoteok", company="Acme Inc", title="AI Engineer")
        b = _make_job(source="eleduck", company="Acme Inc", title="AI Engineer", url="https://example.com/job2")
        assert DedupManager.is_duplicate(a, b) is True

    def test_same_source_not_duplicate(self):
        """Same source should never be flagged as duplicate."""
        a = _make_job(source="remoteok", company="Acme Inc", title="AI Engineer")
        b = _make_job(source="remoteok", company="Acme Inc", title="AI Engineer", url="https://example.com/job2")
        assert DedupManager.is_duplicate(a, b) is False

    def test_cross_source_company_suffix_normalization(self):
        """'Acme Inc' and 'Acme' should match cross-source."""
        a = _make_job(source="remoteok", company="Acme Inc", title="AI Engineer")
        b = _make_job(source="eleduck", company="Acme", title="AI Engineer", url="https://example.com/job2")
        assert DedupManager.is_duplicate(a, b) is True

    def test_cross_source_title_level_normalization(self):
        """'Senior AI Engineer' and 'AI Engineer' should match."""
        a = _make_job(source="remoteok", company="Acme", title="Senior AI Engineer")
        b = _make_job(source="eleduck", company="Acme", title="AI Engineer", url="https://example.com/job2")
        assert DedupManager.is_duplicate(a, b) is True

    def test_cross_source_fuzzy_company(self):
        """Fuzzy company match above threshold."""
        a = _make_job(source="remoteok", company="OpenAI", title="AI Engineer")
        b = _make_job(source="eleduck", company="Open AI", title="AI Engineer", url="https://example.com/job2")
        assert DedupManager.is_duplicate(a, b) is True

    def test_cross_source_fuzzy_title(self):
        """Fuzzy title match above threshold."""
        a = _make_job(source="remoteok", company="Acme", title="Machine Learning Engineer")
        b = _make_job(source="eleduck", company="Acme", title="Machine Learning Eng.", url="https://example.com/job2")
        assert DedupManager.is_duplicate(a, b) is True

    def test_different_company_not_duplicate(self):
        a = _make_job(source="remoteok", company="Acme", title="AI Engineer")
        b = _make_job(source="eleduck", company="Globex", title="AI Engineer", url="https://example.com/job2")
        assert DedupManager.is_duplicate(a, b) is False

    def test_different_title_not_duplicate(self):
        a = _make_job(source="remoteok", company="Acme", title="AI Engineer")
        b = _make_job(source="eleduck", company="Acme", title="Backend Developer", url="https://example.com/job2")
        assert DedupManager.is_duplicate(a, b) is False

    def test_none_company_not_duplicate(self):
        """Jobs with None company should not be matched."""
        a = _make_job(source="remoteok", company=None, title="AI Engineer")
        b = _make_job(source="eleduck", company=None, title="AI Engineer", url="https://example.com/job2")
        assert DedupManager.is_duplicate(a, b) is False

    def test_one_none_company_not_duplicate(self):
        a = _make_job(source="remoteok", company="Acme", title="AI Engineer")
        b = _make_job(source="eleduck", company=None, title="AI Engineer", url="https://example.com/job2")
        assert DedupManager.is_duplicate(a, b) is False


# ===========================================================================
# find_duplicates
# ===========================================================================

class TestFindDuplicates:
    """Tests for DedupManager.find_duplicates."""

    def test_empty_list(self):
        assert DedupManager.find_duplicates([]) == []

    def test_single_job(self):
        assert DedupManager.find_duplicates([_make_job()]) == []

    def test_no_duplicates(self):
        jobs = [
            _make_job(source="remoteok", company="Acme", title="AI Eng"),
            _make_job(source="eleduck", company="Globex", title="Backend Dev", url="https://example.com/j2"),
        ]
        assert DedupManager.find_duplicates(jobs) == []

    def test_finds_cross_source_duplicate(self):
        jobs = [
            _make_job(
                source="remoteok", company="Acme Inc", title="AI Engineer",
                first_seen=datetime(2025, 1, 10),
            ),
            _make_job(
                source="eleduck", company="Acme", title="AI Engineer",
                url="https://example.com/j2",
                first_seen=datetime(2025, 1, 12),
            ),
        ]
        pairs = DedupManager.find_duplicates(jobs)
        assert len(pairs) == 1
        # Original (earlier first_seen) is index 0
        assert pairs[0] == (0, 1)

    def test_original_is_earlier_first_seen(self):
        """The job with earlier first_seen should be the original."""
        jobs = [
            _make_job(
                source="remoteok", company="Acme", title="AI Engineer",
                first_seen=datetime(2025, 1, 15),
            ),
            _make_job(
                source="eleduck", company="Acme", title="AI Engineer",
                url="https://example.com/j2",
                first_seen=datetime(2025, 1, 10),
            ),
        ]
        pairs = DedupManager.find_duplicates(jobs)
        assert len(pairs) == 1
        # Index 1 has earlier first_seen → original
        assert pairs[0] == (1, 0)

    def test_same_source_ignored(self):
        """Same-source pairs should not be flagged."""
        jobs = [
            _make_job(source="remoteok", company="Acme", title="AI Engineer"),
            _make_job(source="remoteok", company="Acme", title="AI Engineer", url="https://example.com/j2"),
        ]
        assert DedupManager.find_duplicates(jobs) == []

    def test_multiple_duplicates(self):
        """Three-way cross-source duplicate: one pair, not two."""
        jobs = [
            _make_job(
                source="remoteok", company="Acme", title="AI Engineer",
                first_seen=datetime(2025, 1, 10),
            ),
            _make_job(
                source="eleduck", company="Acme", title="AI Engineer",
                url="https://example.com/j2",
                first_seen=datetime(2025, 1, 12),
            ),
            _make_job(
                source="weworkremotely", company="Acme Inc", title="AI Engineer",
                url="https://example.com/j3",
                first_seen=datetime(2025, 1, 14),
            ),
        ]
        pairs = DedupManager.find_duplicates(jobs)
        # Job 0 is original, jobs 1 and 2 are duplicates
        assert len(pairs) == 2
        dup_indices = {p[1] for p in pairs}
        orig_indices = {p[0] for p in pairs}
        assert 0 in orig_indices
        assert 1 in dup_indices or 2 in dup_indices


# ===========================================================================
# merge_duplicates
# ===========================================================================

class TestMergeDuplicates:
    """Tests for DedupManager.merge_duplicates."""

    def test_keeps_earliest_first_seen(self):
        original = _make_job(first_seen=datetime(2025, 1, 10), last_seen=datetime(2025, 1, 10))
        duplicate = _make_job(
            source="eleduck", url="https://example.com/j2",
            first_seen=datetime(2025, 1, 8), last_seen=datetime(2025, 1, 12),
        )
        merged = DedupManager.merge_duplicates(original, duplicate)
        assert merged.first_seen == datetime(2025, 1, 8)

    def test_keeps_latest_last_seen(self):
        original = _make_job(first_seen=datetime(2025, 1, 10), last_seen=datetime(2025, 1, 10))
        duplicate = _make_job(
            source="eleduck", url="https://example.com/j2",
            first_seen=datetime(2025, 1, 12), last_seen=datetime(2025, 1, 15),
        )
        merged = DedupManager.merge_duplicates(original, duplicate)
        assert merged.last_seen == datetime(2025, 1, 15)

    def test_merges_tags_union(self):
        original = _make_job(tags=["python", "ai"])
        duplicate = _make_job(
            source="eleduck", url="https://example.com/j2",
            tags=["ai", "ml", "remote"],
        )
        merged = DedupManager.merge_duplicates(original, duplicate)
        assert merged.tags == ["python", "ai", "ml", "remote"]

    def test_preserves_original_fields(self):
        original = _make_job(company="Acme Inc", source="remoteok")
        duplicate = _make_job(
            source="eleduck", company="Acme", url="https://example.com/j2",
        )
        merged = DedupManager.merge_duplicates(original, duplicate)
        assert merged.company == "Acme Inc"
        assert merged.source == "remoteok"
        assert merged.url == "https://example.com/job1"

    def test_no_duplicate_tags(self):
        original = _make_job(tags=["ai", "python"])
        duplicate = _make_job(
            source="eleduck", url="https://example.com/j2",
            tags=["python", "ai"],
        )
        merged = DedupManager.merge_duplicates(original, duplicate)
        assert merged.tags == ["ai", "python"]


# ===========================================================================
# deduplicate (end-to-end)
# ===========================================================================

class TestDeduplicate:
    """Tests for DedupManager.deduplicate (full pipeline)."""

    def test_empty_list(self):
        assert DedupManager.deduplicate([]) == []

    def test_no_duplicates_returns_all(self):
        jobs = [
            _make_job(source="remoteok", company="Acme", title="AI Eng"),
            _make_job(source="eleduck", company="Globex", title="Backend", url="https://example.com/j2"),
        ]
        result = DedupManager.deduplicate(jobs)
        assert len(result) == 2

    def test_removes_cross_source_duplicate(self):
        jobs = [
            _make_job(
                source="remoteok", company="Acme Inc", title="AI Engineer",
                first_seen=datetime(2025, 1, 10), last_seen=datetime(2025, 1, 10),
                tags=["python"],
            ),
            _make_job(
                source="eleduck", company="Acme", title="AI Engineer",
                url="https://example.com/j2",
                first_seen=datetime(2025, 1, 12), last_seen=datetime(2025, 1, 14),
                tags=["remote"],
            ),
        ]
        result = DedupManager.deduplicate(jobs)
        assert len(result) == 1
        assert result[0].source == "remoteok"
        assert result[0].first_seen == datetime(2025, 1, 10)
        assert result[0].last_seen == datetime(2025, 1, 14)
        assert set(result[0].tags) == {"python", "remote"}

    def test_preserves_non_duplicates(self):
        jobs = [
            _make_job(source="remoteok", company="Acme", title="AI Engineer", first_seen=datetime(2025, 1, 10)),
            _make_job(source="eleduck", company="Acme", title="AI Engineer", url="https://example.com/j2", first_seen=datetime(2025, 1, 12)),
            _make_job(source="weworkremotely", company="Globex", title="Backend Dev", url="https://example.com/j3"),
        ]
        result = DedupManager.deduplicate(jobs)
        assert len(result) == 2
        sources = {j.source for j in result}
        assert "weworkremotely" in sources

    def test_same_source_kept(self):
        """Same-source 'duplicates' should both be kept."""
        jobs = [
            _make_job(source="remoteok", company="Acme", title="AI Engineer"),
            _make_job(source="remoteok", company="Acme", title="AI Engineer", url="https://example.com/j2"),
        ]
        result = DedupManager.deduplicate(jobs)
        assert len(result) == 2
