"""Tests for SQLite storage manager."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from scraper.models import JobPosting
from scraper.utils.storage import StorageManager


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup - handle Windows file locking issues
    import time
    import gc
    
    # Force garbage collection to close any lingering connections
    gc.collect()
    
    # Retry deletion with small delay for Windows
    for _ in range(3):
        try:
            Path(db_path).unlink(missing_ok=True)
            break
        except PermissionError:
            time.sleep(0.1)


@pytest.fixture
def storage(temp_db):
    """Create a StorageManager instance with temp database."""
    return StorageManager(db_path=temp_db)


@pytest.fixture
def sample_job():
    """Create a sample job posting for testing."""
    now = datetime.now()
    return JobPosting(
        id="test123",
        title="Senior Python Developer",
        company="Test Corp",
        url="https://example.com/job/123",
        source="remoteok",
        published_at=now,
        salary="$100k-$150k",
        location="Remote",
        description="Great job opportunity",
        tags=["python", "remote", "senior"],
        first_seen=now,
        last_seen=now,
        last_updated=now,
        update_count=1
    )


def test_storage_init_creates_database(temp_db):
    """Test that StorageManager creates database file."""
    storage = StorageManager(db_path=temp_db)
    assert Path(temp_db).exists()


def test_storage_init_creates_tables(storage, temp_db):
    """Test that database has correct schema."""
    import sqlite3
    
    with sqlite3.connect(temp_db) as conn:
        cursor = conn.cursor()
        
        # Check jobs table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='jobs'
        """)
        assert cursor.fetchone() is not None
        
        # Check table has correct columns
        cursor.execute("PRAGMA table_info(jobs)")
        columns = {row[1] for row in cursor.fetchall()}
        expected_columns = {
            "id", "title", "company", "url", "source", "published_at",
            "salary", "location", "description", "tags",
            "first_seen", "last_seen", "last_updated", "update_count", "is_active"
        }
        assert columns == expected_columns


def test_storage_init_creates_indexes(storage, temp_db):
    """Test that database has correct indexes."""
    import sqlite3
    
    with sqlite3.connect(temp_db) as conn:
        cursor = conn.cursor()
        
        # Check indexes exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_%'
        """)
        indexes = {row[0] for row in cursor.fetchall()}
        expected_indexes = {
            "idx_source", "idx_company", "idx_is_active", "idx_first_seen"
        }
        assert indexes == expected_indexes


def test_upsert_job_inserts_new_job(storage, sample_job):
    """Test inserting a new job."""
    new_count, updated_count = storage.upsert_job(sample_job)
    
    assert new_count == 1
    assert updated_count == 0
    
    # Verify job was stored
    jobs = storage.get_all_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == sample_job.id
    assert jobs[0].title == sample_job.title
    assert jobs[0].company == sample_job.company


def test_upsert_job_updates_existing_job(storage, sample_job):
    """Test updating an existing job."""
    # Insert job first
    storage.upsert_job(sample_job)
    
    # Update the job
    sample_job.title = "Updated Title"
    sample_job.last_seen = datetime.now()
    sample_job.last_updated = datetime.now()
    
    new_count, updated_count = storage.upsert_job(sample_job)
    
    assert new_count == 0
    assert updated_count == 1
    
    # Verify job was updated
    jobs = storage.get_all_jobs()
    assert len(jobs) == 1
    assert jobs[0].title == "Updated Title"
    assert jobs[0].update_count == 2  # Should increment


def test_upsert_job_preserves_first_seen(storage, sample_job):
    """Test that first_seen is preserved on update."""
    original_first_seen = sample_job.first_seen
    
    # Insert job
    storage.upsert_job(sample_job)
    
    # Update job with different first_seen
    sample_job.first_seen = datetime.now()
    storage.upsert_job(sample_job)
    
    # Verify first_seen was preserved
    jobs = storage.get_all_jobs()
    assert jobs[0].first_seen == original_first_seen


def test_get_all_jobs_returns_active_only(storage, sample_job):
    """Test that get_all_jobs filters by is_active."""
    import sqlite3
    
    # Insert job
    storage.upsert_job(sample_job)
    
    # Manually set job as inactive
    with sqlite3.connect(storage.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE jobs SET is_active = 0 WHERE id = ?", (sample_job.id,))
        conn.commit()
    
    # Should return empty list with active_only=True
    active_jobs = storage.get_all_jobs(active_only=True)
    assert len(active_jobs) == 0
    
    # Should return job with active_only=False
    all_jobs = storage.get_all_jobs(active_only=False)
    assert len(all_jobs) == 1


def test_get_all_jobs_deserializes_correctly(storage, sample_job):
    """Test that jobs are correctly deserialized from database."""
    storage.upsert_job(sample_job)
    
    jobs = storage.get_all_jobs()
    job = jobs[0]
    
    # Check all fields
    assert job.id == sample_job.id
    assert job.title == sample_job.title
    assert job.company == sample_job.company
    assert job.url == sample_job.url
    assert job.source == sample_job.source
    assert job.salary == sample_job.salary
    assert job.location == sample_job.location
    assert job.description == sample_job.description
    assert job.tags == sample_job.tags
    assert job.update_count == sample_job.update_count


def test_get_all_jobs_handles_null_fields(storage):
    """Test that jobs with NULL fields are deserialized correctly."""
    now = datetime.now()
    job = JobPosting(
        id="test456",
        title="Minimal Job",
        url="https://example.com/job/456",
        source="eleduck",
        first_seen=now,
        last_seen=now,
        last_updated=now
    )
    
    storage.upsert_job(job)
    
    jobs = storage.get_all_jobs()
    assert len(jobs) == 1
    assert jobs[0].company is None
    assert jobs[0].published_at is None
    assert jobs[0].salary is None
    assert jobs[0].location is None
    assert jobs[0].description is None
    assert jobs[0].tags == []


def test_get_stats_returns_correct_counts(storage, sample_job):
    """Test that get_stats returns accurate statistics."""
    import sqlite3
    
    # Insert multiple jobs
    storage.upsert_job(sample_job)
    
    job2 = sample_job.model_copy()
    job2.id = "test456"
    job2.source = "eleduck"
    storage.upsert_job(job2)
    
    job3 = sample_job.model_copy()
    job3.id = "test789"
    job3.source = "weworkremotely"
    storage.upsert_job(job3)
    
    # Mark one job as inactive
    with sqlite3.connect(storage.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE jobs SET is_active = 0 WHERE id = ?", (job3.id,))
        conn.commit()
    
    stats = storage.get_stats()
    
    assert stats["total"] == 3
    assert stats["active"] == 2
    assert stats["inactive"] == 1
    assert stats["by_source"]["remoteok"] == 1
    assert stats["by_source"]["eleduck"] == 1
    assert "weworkremotely" not in stats["by_source"]  # Inactive job not counted


def test_get_stats_empty_database(storage):
    """Test get_stats on empty database."""
    stats = storage.get_stats()
    
    assert stats["total"] == 0
    assert stats["active"] == 0
    assert stats["inactive"] == 0
    assert stats["by_source"] == {}


def test_export_json_creates_file(storage, sample_job, temp_db):
    """Test that export_json creates a valid JSON file."""
    storage.upsert_job(sample_job)
    
    # Export to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        export_path = f.name
    
    try:
        storage.export_json(export_path)
        
        # Verify file exists and is valid JSON
        assert Path(export_path).exists()
        
        with open(export_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert len(data) == 1
        assert data[0]["id"] == sample_job.id
        assert data[0]["title"] == sample_job.title
    finally:
        Path(export_path).unlink(missing_ok=True)


def test_export_json_only_exports_active_jobs(storage, sample_job):
    """Test that export_json only exports active jobs."""
    import sqlite3
    
    # Insert job and mark as inactive
    storage.upsert_job(sample_job)
    
    with sqlite3.connect(storage.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE jobs SET is_active = 0 WHERE id = ?", (sample_job.id,))
        conn.commit()
    
    # Export to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        export_path = f.name
    
    try:
        storage.export_json(export_path)
        
        with open(export_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert len(data) == 0  # No active jobs
    finally:
        Path(export_path).unlink(missing_ok=True)


def test_export_json_creates_parent_directory(storage, sample_job):
    """Test that export_json creates parent directories if needed."""
    storage.upsert_job(sample_job)
    
    # Use a path with non-existent parent directory
    with tempfile.TemporaryDirectory() as tmpdir:
        export_path = Path(tmpdir) / "subdir" / "output.json"
        
        storage.export_json(str(export_path))
        
        assert export_path.exists()
        assert export_path.parent.exists()


def test_multiple_upserts_increment_count(storage, sample_job):
    """Test that multiple upserts correctly increment update_count."""
    # Insert job
    storage.upsert_job(sample_job)
    
    # Update multiple times
    for i in range(5):
        sample_job.last_seen = datetime.now()
        storage.upsert_job(sample_job)
    
    jobs = storage.get_all_jobs()
    assert jobs[0].update_count == 6  # 1 initial + 5 updates


def test_storage_handles_special_characters(storage):
    """Test that storage handles special characters in text fields."""
    now = datetime.now()
    job = JobPosting(
        id="special123",
        title="Developer with 'quotes' and \"double quotes\"",
        company="Test & Co.",
        url="https://example.com/job?id=123&ref=test",
        source="remoteok",
        description="Job with special chars: <html>, {json}, [arrays]",
        tags=["tag-with-dash", "tag_with_underscore", "tag.with.dot"],
        first_seen=now,
        last_seen=now,
        last_updated=now
    )
    
    storage.upsert_job(job)
    
    jobs = storage.get_all_jobs()
    assert len(jobs) == 1
    assert jobs[0].title == job.title
    assert jobs[0].company == job.company
    assert jobs[0].description == job.description
    assert jobs[0].tags == job.tags
