# LiDAR Point Cloud Ingestion Service

Production-ready FastAPI endpoint for ingesting, validating, and extracting metadata from LAS/LAZ LiDAR point cloud files.

## 🎯 Objective

Accept raw LiDAR files (`.las` or `.laz`), validate integrity, extract core metadata from headers (RAM-efficient), and return structured JSON. This is the entry point for all downstream processing in the pipeline.

## 🚀 Quick Start

### Prerequisites
- Python 3.10+ (tested on 3.14)
- pip, virtualenv

### Setup
```bash
# Clone and navigate
git clone <your-repo>
cd arbortech/001

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Run the service
```bash
# Development (with auto-reload)
uvicorn app.main:app --reload

# Production (no reload, bind to all interfaces)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Ensure venv is active, then:
python -m pytest tests/ -v

# Run tests with coverage
# Install coverage plugin if needed
pip install pytest-cov

# Run with terminal coverage report
pytest --cov=app --cov-report=term-missing tests/

# Generate HTML report (optional)
pytest --cov=app --cov-report=html tests/
open htmlcov/index.html  # macOS

# Specific tests
# Happy path
pytest tests/test_utilities.py::test_process_lidar_file_valid -v

# Edge cases (parametrized)
pytest tests/test_utilities.py::test_process_lidar_file_edge_cases -v

# Integration tests (HTTP layer)
pytest tests/test_ingest.py -v
```

### Manual testing with curl
```bash
# Valid upload
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Accept: application/json" \
  -F "file=@/path/to/scan.laz"

# Invalid extension
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@document.txt"
# Response: {"detail":"Invalid file extension. Must be .las or .laz."}

# Corrupted header
# Create a truncated file with valid LAS signature but incomplete header
echo -n "LASF" > corrupt.laz && dd if=/dev/zero bs=1 count=50 >> corrupt.laz 2>/dev/null

curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@corrupt.laz"
# Response: {"detail":"Corrupted or invalid LAS file header"}

# File too large
# Create a 501MB dummy file (requires ~1GB disk space)
dd if=/dev/zero of=large.laz bs=1M count=501 2>/dev/null

curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@large.laz"
# Response: {"detail":"File too large. Maximum size is 500 MB."}

# Cleanup
rm large.laz
```

## Ground Classification Endpoint

### `POST /api/v1/classify/ground`

Classify ground points in a LiDAR point cloud using RANSAC plane segmentation.

**Request**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `file` | `multipart/form-data` | — | `.las` or `.laz` file, ≤ 200 MB |
| `distance_threshold` | `float` | `0.3` | Max distance (meters) for a point to be considered an inlier |
| `ransac_n` | `int` | `3` | Minimum points to define a plane (must be ≥ 3) |
| `num_iterations` | `int` | `100` | RANSAC iterations (higher = more accurate, slower) |

**Success Response (200 OK)**
```json
{
  "ground_point_count": 20520,
  "ground_point_indices": [0, 3, 7, ...],
  "plane_model": [0.002, -0.001, 1.000, 5492.601],
  "points_processed": 100000,
  "processing_time_ms": 691.30,
  "file_hash": "3ce4d90961fbc530..."
}
```

## Test with curl
```bash
# Valid terrain data
curl -X POST http://localhost:8000/api/v1/classify/ground \
  -F "file=@/path/to/terrain.laz"

# Custom RANSAC params (stricter threshold)
curl -X POST "http://localhost:8000/api/v1/classify/ground?distance_threshold=0.1&ransac_n=3&num_iterations=200" \
  -F "file=@/path/to/terrain.laz"

# Invalid param (expect 400)
curl -X POST "http://localhost:8000/api/v1/classify/ground?distance_threshold=-1" \
  -F "file=@/path/to/terrain.laz"
# Response: {"detail":"distance_threshold must be > 0"}
```