# tests/test_utilities.py
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi import UploadFile, HTTPException
from app.utilities import process_lidar_file
from .fixtures.create_test_laz import create_minimal_laz
import tempfile
import shutil

@pytest.fixture
def temp_dir():
    """Provide a temporary directory that auto-cleans."""
    tmp = Path(tempfile.mkdtemp())
    yield tmp
    shutil.rmtree(tmp)

# tests/test_utilities.py

# Add this simple fake class at the top of the file (after imports)
class FakeUploadFile:
    """Minimal fake UploadFile for testing read_laz()."""
    def __init__(self, file_obj, filename: str, size: int):
        self.file = file_obj      # ← The actual file object (sync, seekable)
        self.filename = filename  # ← String filename
        self.size = size          # ← Integer file size


def test_read_laz_valid_file(temp_dir):
    """Happy path: read_laz() processes a valid LAS file correctly."""
    
    # Step 1: Create a minimal valid LAS file
    test_file = temp_dir / "test.las"
    create_minimal_laz(str(test_file))
    
    # Step 2: Create our fake UploadFile (no Mock!)
    with open(test_file, "rb") as f:
        fake_upload = FakeUploadFile(
            file_obj=f,
            filename="test.las",
            size=test_file.stat().st_size
        )
        
        # Step 3: Call the function directly
        result = process_lidar_file(fake_upload, "test.las")
    
    # Step 4: Assert expected output
    assert result["filename"] == "test.las"
    assert result["point_count"] == 3
    assert "bounding_box" in result
    assert result["crs"] is None
    assert "processing_time_ms" in result
    assert isinstance(result["processing_time_ms"], float)

def test_read_laz_invalid_format(temp_dir):
    """Failure mode: uploading a non-LAS file returns 422."""
    
    # Step 1: Create a plain text file (not LAS)
    fake_las = temp_dir / "fake.las"
    fake_las.write_text("This is not a LAS file\n")
    
    # Step 2: Create fake UploadFile wrapping the invalid file
    with open(fake_las, "rb") as f:
        fake_upload = FakeUploadFile(
            file_obj=f,
            filename="fake.las",
            size=fake_las.stat().st_size
        )
        
        # Step 3: Call read_laz() and expect it to raise HTTPException(422)
        # Prompt: How do you assert an exception is raised in pytest?
        # Hint: pytest.raises()
        
        with pytest.raises(HTTPException) as exc_info:
            process_lidar_file(fake_upload, "fake.las")
        
        # Step 4: Assert the exception has the correct status code
        assert exc_info.value.status_code == 400
        assert "Corrupted or invalid LAS file header" in exc_info.value.detail

def test_read_laz_corrupt_header(temp_dir):
    """Failure mode: LAS file with valid extension but truncated header → 422."""
    
    # Step 1: Create a file with LAS signature but truncated content
    corrupt_las = temp_dir / "corrupt.las"
    # Write just the LAS magic bytes + partial header (not a full valid file)
    with open(corrupt_las, "wb") as f:
        f.write(b"LASF")  # Valid LAS signature
        f.write(b"\x00" * 50)  # Incomplete header → laspy will fail
    
    # Step 2: Create fake UploadFile wrapping the corrupt file
    with open(corrupt_las, "rb") as f:
        fake_upload = FakeUploadFile(
            file_obj=f,
            filename="corrupt.las",
            size=corrupt_las.stat().st_size
        )
        
        # Step 3: Assert read_laz() raises HTTPException(422)
        with pytest.raises(HTTPException) as exc_info:
            process_lidar_file(fake_upload, "corrupt.las")
        
        # Step 4: Verify correct status code and generic detail
        assert exc_info.value.status_code == 400
        assert "Corrupted or invalid LAS file header" in exc_info.value.detail

@pytest.mark.parametrize(
    "filename,content,expected_detail",
    [
        # Invalid extension: .txt renamed to .las
        ("scan.txt.las", b"This is not a LAS file\n", "Corrupted or invalid LAS file header"),
        # Corrupted header: truncated LAS signature
        ("corrupt.las", b"LASF" + b"\x00" * 50, "Corrupted or invalid LAS file header"),
    ],
)
def test_read_laz_edge_cases(temp_dir, filename, content, expected_detail):
    """Parametrized edge-case tests: invalid extension or corrupted header → 400."""
    
    # Step 1: Write test content to temp file
    test_file = temp_dir / filename
    test_file.write_bytes(content)
    
    # Step 2: Create FakeUploadFile using BytesIO (as requested)
    from io import BytesIO
    with open(test_file, "rb") as f:
        fake_upload = FakeUploadFile(
            file_obj=BytesIO(content),  # ← BytesIO per employer request
            filename=filename,
            size=len(content)
        )
        
        # Step 3: Assert HTTPException with correct status and detail
        with pytest.raises(HTTPException) as exc_info:
            process_lidar_file(fake_upload, filename)
        
        assert exc_info.value.status_code == 400
        assert expected_detail in exc_info.value.detail