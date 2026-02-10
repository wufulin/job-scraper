from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pytest

from scraper.models import JobPosting
from tests.fakes.storage import FakeStorage


def _make_job(
    *,
    id: str = "abc123",
    title: str = "AI Engineer",
    company: str = "TestCorp",
    url: str = "https://example.com/job/1",
    source: str = "remoteok",
    tags: Optional[list[str]] = None,
    published_at: Optional[datetime] = None,
    first_seen: Optional[datetime] = None,
) -> JobPosting:
    now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    return JobPosting(
        id=id,
        title=title,
        company=company,
        url=url,
        source=source,
        description="Build AI models",
        tags=tags or ["ai", "remote"],
        published_at=published_at or now,
        first_seen=first_seen or now,
        last_seen=now,
        last_updated=now,
        update_count=1,
    )


@pytest.fixture
def storage() -> FakeStorage:
    return FakeStorage()


class TestUpsertJob:

    async def test_insert_new_job(self, storage: FakeStorage) -> None:
        job = _make_job()
        new, updated = await storage.upsert_job(job)

        assert new == 1
        assert updated == 0

    async def test_update_existing_job(self, storage: FakeStorage) -> None:
        job = _make_job()
        await storage.upsert_job(job)
        new, updated = await storage.upsert_job(job)

        assert new == 0
        assert updated == 1

    async def test_update_increments_update_count(self, storage: FakeStorage) -> None:
        job = _make_job()
        await storage.upsert_job(job)
        await storage.upsert_job(job)
        await storage.upsert_job(job)

        row = await storage.get_job_by_id(job.id)
        assert row is not None
        assert row["update_count"] == 3

    async def test_update_preserves_first_seen(self, storage: FakeStorage) -> None:
        original_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        job = _make_job(first_seen=original_time)
        await storage.upsert_job(job)

        later_time = datetime(2025, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
        updated_job = _make_job(first_seen=later_time)
        await storage.upsert_job(updated_job)

        row = await storage.get_job_by_id(job.id)
        assert row is not None
        assert row["first_seen"] == original_time

    async def test_upsert_stores_tags_as_list(self, storage: FakeStorage) -> None:
        job = _make_job(tags=["python", "ai", "remote"])
        await storage.upsert_job(job)

        row = await storage.get_job_by_id(job.id)
        assert row is not None
        assert isinstance(row["tags"], list)
        assert row["tags"] == ["python", "ai", "remote"]


class TestUpsertJobsBatch:

    async def test_batch_inserts_multiple_jobs(self, storage: FakeStorage) -> None:
        jobs = [
            _make_job(id="job1", title="AI Engineer", source="remoteok"),
            _make_job(id="job2", title="ML Engineer", source="eleduck"),
            _make_job(id="job3", title="Data Scientist", source="remoteok"),
        ]
        new, updated = await storage.upsert_jobs_batch(jobs)

        assert new == 3
        assert updated == 0

    async def test_batch_mixed_insert_and_update(self, storage: FakeStorage) -> None:
        existing = _make_job(id="job1", title="AI Engineer", source="remoteok")
        await storage.upsert_job(existing)

        jobs = [
            _make_job(id="job1", title="AI Engineer", source="remoteok"),
            _make_job(id="job2", title="ML Engineer", source="eleduck"),
        ]
        new, updated = await storage.upsert_jobs_batch(jobs)

        assert new == 1
        assert updated == 1

    async def test_batch_empty_list(self, storage: FakeStorage) -> None:
        new, updated = await storage.upsert_jobs_batch([])

        assert new == 0
        assert updated == 0


class TestGetAllJobs:

    async def test_returns_empty_list_when_no_jobs(self, storage: FakeStorage) -> None:
        rows = await storage.get_all_jobs()
        assert rows == []

    async def test_returns_all_stored_jobs(self, storage: FakeStorage) -> None:
        await storage.upsert_job(_make_job(id="job1", source="remoteok"))
        await storage.upsert_job(_make_job(id="job2", source="eleduck"))

        rows = await storage.get_all_jobs()
        assert len(rows) == 2

    async def test_filters_by_source(self, storage: FakeStorage) -> None:
        await storage.upsert_job(_make_job(id="job1", source="remoteok"))
        await storage.upsert_job(_make_job(id="job2", source="eleduck"))
        await storage.upsert_job(_make_job(id="job3", source="remoteok"))

        rows = await storage.get_all_jobs(source="remoteok")
        assert len(rows) == 2
        assert all(r["source"] == "remoteok" for r in rows)

    async def test_source_filter_no_match(self, storage: FakeStorage) -> None:
        await storage.upsert_job(_make_job(id="job1", source="remoteok"))

        rows = await storage.get_all_jobs(source="eleduck")
        assert rows == []

    async def test_sorted_by_first_seen_descending(self, storage: FakeStorage) -> None:
        early = datetime(2025, 1, 1, tzinfo=timezone.utc)
        mid = datetime(2025, 6, 1, tzinfo=timezone.utc)
        late = datetime(2025, 12, 1, tzinfo=timezone.utc)

        await storage.upsert_job(_make_job(id="early", first_seen=early, source="remoteok"))
        await storage.upsert_job(_make_job(id="late", first_seen=late, source="remoteok"))
        await storage.upsert_job(_make_job(id="mid", first_seen=mid, source="remoteok"))

        rows = await storage.get_all_jobs()
        assert [r["id"] for r in rows] == ["late", "mid", "early"]

    async def test_returns_deep_copies(self, storage: FakeStorage) -> None:
        await storage.upsert_job(_make_job(id="job1", source="remoteok"))

        rows = await storage.get_all_jobs()
        rows[0]["title"] = "MUTATED"

        original = await storage.get_job_by_id("job1")
        assert original is not None
        assert original["title"] != "MUTATED"


class TestGetJobById:

    async def test_returns_existing_job(self, storage: FakeStorage) -> None:
        job = _make_job(id="target")
        await storage.upsert_job(job)

        row = await storage.get_job_by_id("target")
        assert row is not None
        assert row["id"] == "target"
        assert row["title"] == "AI Engineer"
        assert row["company"] == "TestCorp"

    async def test_returns_none_for_missing_id(self, storage: FakeStorage) -> None:
        row = await storage.get_job_by_id("nonexistent")
        assert row is None

    async def test_returned_dict_has_all_fields(self, storage: FakeStorage) -> None:
        job = _make_job()
        await storage.upsert_job(job)

        row = await storage.get_job_by_id(job.id)
        assert row is not None
        expected_keys = {
            "id", "title", "company", "url", "source", "published_at",
            "salary", "location", "description", "tags",
            "first_seen", "last_seen", "last_updated", "update_count", "is_active",
        }
        assert set(row.keys()) == expected_keys


class TestGetStats:

    async def test_empty_storage_stats(self, storage: FakeStorage) -> None:
        stats = await storage.get_stats()
        assert stats["total"] == 0
        assert stats["by_source"] == {}

    async def test_stats_counts_by_source(self, storage: FakeStorage) -> None:
        await storage.upsert_job(_make_job(id="j1", source="remoteok"))
        await storage.upsert_job(_make_job(id="j2", source="remoteok"))
        await storage.upsert_job(_make_job(id="j3", source="eleduck"))

        stats = await storage.get_stats()
        assert stats["total"] == 3
        assert stats["by_source"]["remoteok"] == 2
        assert stats["by_source"]["eleduck"] == 1


class TestExportJobs:

    async def test_export_returns_all_jobs(self, storage: FakeStorage) -> None:
        await storage.upsert_job(_make_job(id="j1", source="remoteok"))
        await storage.upsert_job(_make_job(id="j2", source="eleduck"))

        exported = await storage.export_jobs()
        assert len(exported) == 2

    async def test_export_filters_by_source(self, storage: FakeStorage) -> None:
        await storage.upsert_job(_make_job(id="j1", source="remoteok"))
        await storage.upsert_job(_make_job(id="j2", source="eleduck"))

        exported = await storage.export_jobs(source="eleduck")
        assert len(exported) == 1
        assert exported[0]["source"] == "eleduck"


class TestHealthCheck:

    async def test_healthy_by_default(self, storage: FakeStorage) -> None:
        assert await storage.health_check() is True

    async def test_unhealthy_when_set(self, storage: FakeStorage) -> None:
        storage._healthy = False
        assert await storage.health_check() is False


class TestStorageProtocolCompliance:

    async def test_fake_storage_has_all_protocol_methods(self) -> None:
        from app.services.storage import StorageProtocol

        required_methods = [
            "init_pool",
            "close_pool",
            "upsert_job",
            "upsert_jobs_batch",
            "get_all_jobs",
            "get_job_by_id",
            "get_stats",
            "export_jobs",
            "health_check",
        ]
        for method_name in required_methods:
            assert hasattr(FakeStorage, method_name), f"FakeStorage missing {method_name}"

    async def test_fake_storage_is_structural_subtype(self) -> None:
        from app.services.storage import StorageProtocol

        storage: StorageProtocol = FakeStorage()
        assert isinstance(storage, StorageProtocol)
