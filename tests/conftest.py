import pytest
from fastapi.testclient import TestClient
from app.main import app
import tempfile
import shutil
from pathlib import Path

@pytest.fixture
def client():
    # Provide a TestClient instance for API tests.
    with TestClient(app) as c:
        yield c

@pytest.fixture
def temp_dir():
    # Provide temporary directory that auto-cleans
    tmp = Path(tempfile.mkdtemp())
    yield tmp
    shutil.rmtree(tmp) # cleanup after test

from unittest.mock import patch

@pytest.fixture
def small_file_limit():
    """Temporarily lower MAX_FILE_SIZE for testing."""
    with patch("app.main.MAX_FILE_SIZE", 100):  # 100 bytes limit
        yield