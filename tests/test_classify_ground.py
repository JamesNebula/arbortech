# tests/test_classify_ground.py
"""Tests for the ground classification endpoint.

All tests run offline using synthetic data generated with laspy.
No external files or network calls required.
"""
import pytest
import numpy as np
import laspy
from fastapi.testclient import TestClient

from app.main import app
from app.config import MAX_POINTS_FOR_RANSAC

# Initialize TestClient once for all tests
client = TestClient(app)


# ============================================================================
# FIXTURES
# ============================================================================
@pytest.fixture
def synthetic_planar_las(tmp_path):
    """Generate a minimal LAS file with a synthetic planar ground + small noise.
    
    Creates 1,000 points on a horizontal plane (z=100) with ±5cm Gaussian noise.
    This simulates flat terrain that RANSAC should easily classify as ground.
    
    Args:
        tmp_path: pytest's built-in tmp_path fixture (auto-cleanup)
    
    Returns:
        Path: Path to the generated .las file
    """
    # Generate synthetic planar ground points
    n_points = 1000
    rng = np.random.default_rng(42)  # Reproducible noise
    
    x = rng.uniform(0, 100, n_points)
    y = rng.uniform(0, 100, n_points)
    z = np.full(n_points, 100.0) + rng.normal(0, 0.05, n_points)  # ±5cm noise
    
    # Create minimal valid LAS 1.4 header (point format 6)
    header = laspy.LasHeader(version="1.4", point_format=6)
    header.scales = np.array([0.01, 0.01, 0.01])  # 1cm precision
    header.offsets = np.array([0.0, 0.0, 0.0])
    
    # Create LasData and assign points
    las = laspy.LasData(header)
    las.x = x
    las.y = y
    las.z = z
    
    # Write to temp file (auto-cleanup via tmp_path)
    output_path = tmp_path / "planar_ground.las"
    las.write(str(output_path))
    
    return output_path


# ============================================================================
# TESTS
# ============================================================================
def test_classify_ground_happy_path(synthetic_planar_las):
    """Happy path: valid planar LAS → returns non-empty ground indices."""
    
    # Upload the synthetic file
    with open(synthetic_planar_las, "rb") as f:
        files = {"file": ("planar_ground.las", f, "application/octet-stream")}
        response = client.post("/api/v1/classify/ground", files=files)
    
    # Assert HTTP success
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    # Parse and validate response schema
    data = response.json()
    
    # Core fields must exist and have correct types
    assert isinstance(data["ground_point_count"], int)
    assert data["ground_point_count"] > 0, "Should find at least some ground points on planar data"
    
    assert isinstance(data["ground_point_indices"], list)
    assert len(data["ground_point_indices"]) == data["ground_point_count"]
    
    assert isinstance(data["plane_model"], list)
    assert len(data["plane_model"]) == 4, "Plane model must be [a, b, c, d]"
    
    assert isinstance(data["points_processed"], int)
    assert data["points_processed"] <= MAX_POINTS_FOR_RANSAC
    
    assert isinstance(data["processing_time_ms"], (int, float))
    assert data["processing_time_ms"] >= 0
    
    assert isinstance(data["file_hash"], str)
    assert len(data["file_hash"]) == 64, "SHA-256 hash must be 64 hex chars"
    
    # Bonus validation: plane normal should be roughly horizontal for ground terrain
    # Plane equation: ax + by + cz + d = 0 → normal vector = [a, b, c]
    # For horizontal ground, normal ≈ [0, 0, 1], so |c| should dominate
    a, b, c, d = data["plane_model"]
    normal_magnitude = (a**2 + b**2 + c**2) ** 0.5
    c_normalized = abs(c) / normal_magnitude if normal_magnitude > 0 else 0
    
    assert c_normalized > 0.9, f"Ground plane normal should be Z-dominant, got c={c_normalized:.3f}"