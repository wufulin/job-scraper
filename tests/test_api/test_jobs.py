from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from scraper.models import JobPosting


def _make_job(
    *,
    id: str = "abc123",
    title: str = "AI Engineer",
    company: str = "TestCorp",
    url: str = "https://example.com/job/1",
    source: str = "remoteok",
    description: str = "Build AI models",
    tags: list[str] | None = None,
    salary: str | None = None,
    location: str | None = "Remote",
) -> JobPosting:
    now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    return JobPosting(
        id=id,
        title=title,
        company=company,
        url=url,
        source=source,
        description=description,
        tags=tags or ["ai", "remote"],
        salary=salary,
        location=location,
        published_at=now,
        first_seen=now,
        last_seen=now,
        last_updated=now,
        update_count=1,
    )


SAMPLE_JOBS = [
    _make_job(id="job1", title="AI Engineer", source="remoteok", description="Build ML models"),
    _make_job(id="job2", title="Backend Developer", source="eleduck", company="RemoteCo", description="Python backend"),
    _make_job(id="job3", title="ML Researcher", source="remoteok", description="Research AI safety"),
    _make_job(id="job4", title="Frontend Dev", source="weworkremotely", description="React dashboard"),
    _make_job(id="job5", title="Data Scientist", source="eleduck", description="AI data pipelines"),
]


def _mock_storage() -> AsyncMock:
    storage = AsyncMock()
    storage.get_all_jobs = AsyncMock(return_value=SAMPLE_JOBS)
    return storage


class TestListJobs:

    async def test_list_jobs_returns_200(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs")

        assert response.status_code == 200

    async def test_list_jobs_returns_paginated_data(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs?page=1&per_page=2")

        data = response.json()
        assert len(data["data"]) == 2
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 2
        assert data["pagination"]["total"] == 5
        assert data["pagination"]["total_pages"] == 3

    async def test_list_jobs_page_2(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs?page=2&per_page=2")

        data = response.json()
        assert len(data["data"]) == 2
        assert data["pagination"]["page"] == 2

    async def test_list_jobs_last_page_partial(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs?page=3&per_page=2")

        data = response.json()
        assert len(data["data"]) == 1

    async def test_list_jobs_filter_by_source(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs?source=eleduck")

        data = response.json()
        assert data["pagination"]["total"] == 2
        assert all(j["source"] == "eleduck" for j in data["data"])

    async def test_list_jobs_empty_page_returns_empty_data(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs?page=999")

        data = response.json()
        assert data["data"] == []
        assert data["pagination"]["total"] == 5

    async def test_list_jobs_default_pagination(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs")

        data = response.json()
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 20
        assert len(data["data"]) == 5

    async def test_list_jobs_contains_expected_fields(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs")

        job = response.json()["data"][0]
        expected_fields = {
            "id", "title", "company", "url", "source", "published_at",
            "salary", "location", "description", "tags",
            "first_seen", "last_seen", "last_updated", "update_count",
        }
        assert set(job.keys()) == expected_fields


class TestGetJob:

    async def test_get_existing_job(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs/job1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "job1"
        assert data["title"] == "AI Engineer"

    async def test_get_nonexistent_job_returns_404(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestSearchJobs:

    async def test_search_matches_title_and_description(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs/search?q=AI")

        assert response.status_code == 200
        data = response.json()
        # "AI" in title: job1; "AI" in description: job3, job5
        assert data["pagination"]["total"] == 3
        titles = [j["title"] for j in data["data"]]
        assert "AI Engineer" in titles

    async def test_search_matches_description_only(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs/search?q=pipelines")

        data = response.json()
        assert data["pagination"]["total"] == 1
        assert data["data"][0]["title"] == "Data Scientist"

    async def test_search_case_insensitive(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs/search?q=backend")

        data = response.json()
        assert data["pagination"]["total"] >= 1
        titles = [j["title"] for j in data["data"]]
        assert "Backend Developer" in titles

    async def test_search_no_results(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs/search?q=zzzznotfound")

        data = response.json()
        assert data["data"] == []
        assert data["pagination"]["total"] == 0

    async def test_search_with_source_filter(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs/search?q=AI&source=remoteok")

        data = response.json()
        assert all(j["source"] == "remoteok" for j in data["data"])

    async def test_search_with_pagination(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs/search?q=AI&page=1&per_page=1")

        data = response.json()
        assert len(data["data"]) == 1
        assert data["pagination"]["per_page"] == 1

    async def test_search_missing_query_returns_422(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs/search")

        assert response.status_code == 422

    async def test_search_returns_timezone_aware_datetimes(self) -> None:
        with patch("app.routers.jobs.get_job_service") as mock_svc_factory:
            from app.services.job_service import JobService

            mock_svc_factory.return_value = JobService(storage=_mock_storage())
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/jobs/search?q=AI")

        data = response.json()
        if data["data"]:
            job = data["data"][0]
            for field in ["first_seen", "last_seen", "last_updated"]:
                ts = datetime.fromisoformat(job[field])
                assert ts.tzinfo is not None, f"{field} must be timezone-aware"
