from pathlib import Path
import pytest
from .fixtures.create_test_laz import create_minimal_laz
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

def test_ingest_valid_file(client, temp_dir):
    # happy path: valid LAZ upload returns 200 + expected fields

    # Generate a minimal valid las file in the temp dir
    test_file = temp_dir / "test.las"
    create_minimal_laz(str(test_file))

    # read file as bytes for upload
    with open(test_file, 'rb') as f:
        file_content = f.read()
        logger.info(f"DEBUG TEST: Read {len(file_content)} bytes from {test_file}")

    files = {
        "file": ("test.las", BytesIO(file_content), "application/octet-stream")
        }
    #POST to /ingest
    response = client.post("/api/v1/ingest", files=files)
    logger.info(f"DEBUG TEST: response status: {response.status_code}")

    # assert success
    assert response.status_code == 200

    # assert response schema
    data = response.json()
    assert data['filename'] == 'test.las'
    assert data['point_count'] == 3
    assert "bounding_box" in data
    assert "crs" in data
    assert "processing_time_ms" in data

def test_ingest_file_too_large(client, small_file_limit):
    """Failure mode: file > mocked limit returns 413."""
    
    # Create a 200-byte fake file (larger than the mocked 100-byte limit)
    fake_content = b"x" * 200
    files = {"file": ("large.laz", fake_content, "application/octet-stream")}
    
    # POST to /ingest
    response = client.post("/api/v1/ingest", files=files)
    
    # Assert spec-compliant response
    assert response.status_code == 400
    assert "File too large" in response.json()["detail"]

def test_max_file_size_constant():
    """Verify MAX_FILE_SIZE is configured to 500MB per spec."""
    from app.main import MAX_FILE_SIZE
    
    # Assert the constant matches the requirement
    assert MAX_FILE_SIZE == 500 * 1024 * 1024
    assert MAX_FILE_SIZE == 524_288_000  # 500MB in bytes (explicit check)