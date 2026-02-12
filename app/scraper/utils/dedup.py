"""Cross-site job deduplication utility.

Detects and merges duplicate job postings across different sources
using company name and title similarity matching.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Optional

from app.scraper.models import JobPosting


# Suffixes to strip when normalizing company names
_COMPANY_SUFFIXES = re.compile(
    r"\b(inc|ltd|llc|corp|co|gmbh|limited|incorporated)\.?(?=\s|$)",
    re.IGNORECASE,
)

# Role-level prefixes to strip when normalizing titles
_TITLE_LEVEL_WORDS = re.compile(
    r"\b(senior|junior|lead|staff|principal|intern|sr|jr)\.?(?=\s|$)",
    re.IGNORECASE,
)

# Collapse multiple whitespace into single space
_MULTI_SPACE = re.compile(r"\s+")

# Fuzzy match threshold
SIMILARITY_THRESHOLD = 0.85


class DedupManager:
    """Detects and merges duplicate jobs across different sources.

    Only considers cross-source duplicates (same source duplicates
    are handled by the per-source ID-based upsert in storage).
    """

    @staticmethod
    def normalize_company(company: Optional[str]) -> str:
        """Normalize company name for comparison.

        Lowercases, strips common suffixes (Inc, Ltd, LLC, etc.),
        and collapses whitespace.

        Args:
            company: Raw company name, may be None.

        Returns:
            Normalized company string (empty string if None).
        """
        if not company:
            return ""
        text = company.lower().strip()
        text = _COMPANY_SUFFIXES.sub("", text)
        text = _MULTI_SPACE.sub(" ", text).strip()
        return text

    @staticmethod
    def normalize_title(title: str) -> str:
        """Normalize job title for comparison.

        Lowercases, strips seniority-level words (Senior, Junior, Lead),
        and collapses whitespace.

        Args:
            title: Raw job title.

        Returns:
            Normalized title string.
        """
        text = title.lower().strip()
        text = _TITLE_LEVEL_WORDS.sub("", text)
        text = _MULTI_SPACE.sub(" ", text).strip()
        return text

    @staticmethod
    def similarity(a: str, b: str) -> float:
        """Compute similarity ratio between two strings.

        Uses difflib.SequenceMatcher for fuzzy comparison.

        Args:
            a: First string.
            b: Second string.

        Returns:
            Float between 0.0 and 1.0.
        """
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a, b).ratio()

    @classmethod
    def is_duplicate(cls, job_a: JobPosting, job_b: JobPosting) -> bool:
        """Determine whether two jobs are cross-source duplicates.

        Two jobs are duplicates when:
        - They come from different sources (cross-source only).
        - Their normalized companies match exactly OR fuzzy > threshold.
        - Their normalized titles match exactly OR fuzzy > threshold.

        Args:
            job_a: First job posting.
            job_b: Second job posting.

        Returns:
            True if the pair is a cross-source duplicate.
        """
        # Must be cross-source
        if job_a.source == job_b.source:
            return False

        # Both must have a company to compare
        comp_a = cls.normalize_company(job_a.company)
        comp_b = cls.normalize_company(job_b.company)
        if not comp_a or not comp_b:
            return False

        # Company match: exact or fuzzy
        company_match = (
            comp_a == comp_b
            or cls.similarity(comp_a, comp_b) > SIMILARITY_THRESHOLD
        )
        if not company_match:
            return False

        # Title match: exact or fuzzy
        title_a = cls.normalize_title(job_a.title)
        title_b = cls.normalize_title(job_b.title)
        title_match = (
            title_a == title_b
            or cls.similarity(title_a, title_b) > SIMILARITY_THRESHOLD
        )
        return title_match

    @classmethod
    def find_duplicates(cls, jobs: list[JobPosting]) -> list[tuple[int, int]]:
        """Find all cross-source duplicate pairs in a list of jobs.

        Normalizes company/title once per job, then checks all
        cross-source pairs for exact or fuzzy matches.

        Args:
            jobs: List of JobPosting objects from multiple sources.

        Returns:
            List of (original_index, duplicate_index) tuples. The
            original is the one with the earlier first_seen; the
            duplicate is the later one.
        """
        if len(jobs) < 2:
            return []

        # Pre-compute normalized values
        normalized = [
            (cls.normalize_company(j.company), cls.normalize_title(j.title))
            for j in jobs
        ]

        duplicates: list[tuple[int, int]] = []
        seen_duplicates: set[int] = set()

        for i in range(len(jobs)):
            if i in seen_duplicates:
                continue
            for j in range(i + 1, len(jobs)):
                if j in seen_duplicates:
                    continue
                # Cross-source only
                if jobs[i].source == jobs[j].source:
                    continue

                comp_i, title_i = normalized[i]
                comp_j, title_j = normalized[j]

                # Skip if either company is empty
                if not comp_i or not comp_j:
                    continue

                # Company match
                company_match = (
                    comp_i == comp_j
                    or cls.similarity(comp_i, comp_j) > SIMILARITY_THRESHOLD
                )
                if not company_match:
                    continue

                # Title match
                title_match = (
                    title_i == title_j
                    or cls.similarity(title_i, title_j) > SIMILARITY_THRESHOLD
                )
                if not title_match:
                    continue

                # Determine original (earlier first_seen) vs duplicate
                if jobs[i].first_seen <= jobs[j].first_seen:
                    duplicates.append((i, j))
                    seen_duplicates.add(j)
                else:
                    duplicates.append((j, i))
                    seen_duplicates.add(i)

        return duplicates

    @staticmethod
    def merge_duplicates(original: JobPosting, duplicate: JobPosting) -> JobPosting:
        """Merge duplicate into original, preserving the best data.

        Keeps:
        - The earliest first_seen.
        - The latest last_seen.
        - Union of tags from both.
        - All other fields from the original.

        Args:
            original: The job to keep (usually earliest first_seen).
            duplicate: The duplicate to merge from.

        Returns:
            New JobPosting with merged metadata.
        """
        merged_first_seen = min(original.first_seen, duplicate.first_seen)
        merged_last_seen = max(original.last_seen, duplicate.last_seen)
        merged_tags = list(dict.fromkeys(original.tags + duplicate.tags))

        return original.model_copy(
            update={
                "first_seen": merged_first_seen,
                "last_seen": merged_last_seen,
                "tags": merged_tags,
            }
        )

    @classmethod
    def deduplicate(cls, jobs: list[JobPosting]) -> list[JobPosting]:
        """Remove cross-source duplicates from a list of jobs.

        Finds duplicates, merges them into originals, and returns a
        deduplicated list (order preserved, duplicates removed).

        Args:
            jobs: List of JobPosting objects from multiple sources.

        Returns:
            Deduplicated list with merged metadata.
        """
        pairs = cls.find_duplicates(jobs)
        if not pairs:
            return list(jobs)

        # Build set of duplicate indices and merge map
        duplicate_indices: set[int] = set()
        merged: dict[int, JobPosting] = {}

        for orig_idx, dup_idx in pairs:
            duplicate_indices.add(dup_idx)
            base = merged.get(orig_idx, jobs[orig_idx])
            merged[orig_idx] = cls.merge_duplicates(base, jobs[dup_idx])

        # Build result preserving order
        result: list[JobPosting] = []
        for i, job in enumerate(jobs):
            if i in duplicate_indices:
                continue
            result.append(merged.get(i, job))

        return result
