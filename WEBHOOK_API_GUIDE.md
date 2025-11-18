# Webhook Server & API Integration Guide

**Version:** 1.0.0
**Last Updated:** November 18, 2025

---

## Overview

The Zarr Benchmarks webhook server enables automated benchmark integration with imaging pipelines. Submit benchmark jobs via REST API, process them asynchronously, and retrieve results programmatically.

## Features

- **REST API**: HTTP endpoints for job submission and status checking
- **Asynchronous Processing**: Queue-based job management
- **Multi-Modal Support**: 10+ imaging modalities (CryoET, light sheet, confocal, etc.)
- **Compression Profiles**: Pre-configured recommendations (archival, balanced, fast)
- **Real-Time Status**: Monitor job progress and retrieve results

---

## Quick Start

### 1. Start the Webhook Server

```bash
# Install dependencies
pip install -e ".[plots]"
pip install aiohttp

# Start server (default port 8080)
python benchmark_webhook_server.py

# Custom port
python benchmark_webhook_server.py --port 8888
```

**Server runs at**: `http://localhost:8080`

### 2. Submit a Benchmark Job

```bash
# Using curl
curl -X POST http://localhost:8080/benchmark \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_type": "cryoet",
    "shape": [256, 256, 256],
    "voxel_size": [2.5, 2.5, 2.5],
    "compression_profile": "balanced"
  }'
```

**Response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "status": "pending",
  "message": "Benchmark job queued successfully"
}
```

### 3. Check Job Status

```bash
curl http://localhost:8080/status/a1b2c3d4-e5f6-7890-1234-567890abcdef
```

**Response (running):**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "status": "running",
  "submitted_at": "2025-11-18T21:30:00Z",
  "started_at": "2025-11-18T21:30:02Z"
}
```

**Response (completed):**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "status": "completed",
  "submitted_at": "2025-11-18T21:30:00Z",
  "started_at": "2025-11-18T21:30:02Z",
  "completed_at": "2025-11-18T21:32:15Z",
  "results": {
    "best_compression": {
      "codec": "blosc_zstd",
      "level": 5,
      "ratio": 1.17,
      "write_time": 0.013,
      "read_time": 0.004
    },
    "recommendations": {
      "archival": "blosc_zstd_5",
      "fast": "blosc_lz4_3",
      "balanced": "blosc_zstd_3"
    }
  }
}
```

---

## API Reference

### Endpoints

#### `POST /benchmark`

Submit a new benchmark job.

**Request Body:**
```json
{
  "dataset_type": "cryoet",           // Required: Dataset type
  "shape": [256, 256, 256],           // Required: Volume dimensions
  "voxel_size": [2.5, 2.5, 2.5],     // Optional: Physical voxel size (nm)
  "compression_profile": "balanced",  // Optional: archival|balanced|fast|lossless
  "custom_codecs": ["blosc_zstd"],   // Optional: Specific codecs to test
  "chunk_sizes": [[64,64,64]]        // Optional: Custom chunk sizes
}
```

**Response:** `201 Created`
```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Benchmark job queued successfully"
}
```

---

#### `GET /status/{job_id}`

Check status of a benchmark job.

**Response:** `200 OK`
```json
{
  "job_id": "uuid",
  "status": "pending|running|completed|failed",
  "submitted_at": "ISO-8601 timestamp",
  "started_at": "ISO-8601 timestamp or null",
  "completed_at": "ISO-8601 timestamp or null",
  "results": { /* benchmark results if completed */ },
  "error": "error message if failed"
}
```

---

#### `GET /health`

Check server health.

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "jobs": {
    "pending": 2,
    "running": 1,
    "completed": 15,
    "failed": 0
  }
}
```

---

## Supported Dataset Types

### Available Modalities

```python
class DatasetType(Enum):
    CRYOET = "cryoet"              # Cryo-electron tomography
    LIGHT_SHEET = "light_sheet"    # Light sheet microscopy
    CONFOCAL = "confocal"          # Confocal microscopy
    TWO_PHOTON = "two_photon"      # Two-photon microscopy
    WIDEFIELD = "widefield"        # Widefield microscopy
    SEM = "sem"                    # Scanning electron microscopy
    STED = "sted"                  # STED super-resolution
    PALM_STORM = "palm_storm"      # PALM/STORM localization
    SYNTHETIC = "synthetic"        # Synthetic test data
    CUSTOM = "custom"              # User-defined
```

### Compression Profiles

```python
class CompressionProfile(Enum):
    ARCHIVAL = "archival"    # Maximum compression, slower
    BALANCED = "balanced"    # Good compression, reasonable speed
    FAST = "fast"            # Light compression, maximum speed
    LOSSLESS = "lossless"    # Guaranteed lossless
    ANALYSIS = "analysis"    # Optimized for analysis workflows
```

---

## Python Client Example

```python
import requests
import time
import json

class BenchmarkClient:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url

    def submit_benchmark(self, dataset_type, shape, voxel_size=None,
                         compression_profile="balanced"):
        """Submit a benchmark job."""
        data = {
            "dataset_type": dataset_type,
            "shape": shape,
            "compression_profile": compression_profile
        }
        if voxel_size:
            data["voxel_size"] = voxel_size

        response = requests.post(
            f"{self.base_url}/benchmark",
            json=data
        )
        response.raise_for_status()
        return response.json()

    def get_status(self, job_id):
        """Get status of a benchmark job."""
        response = requests.get(f"{self.base_url}/status/{job_id}")
        response.raise_for_status()
        return response.json()

    def wait_for_completion(self, job_id, poll_interval=5, timeout=300):
        """Wait for job to complete."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status_data = self.get_status(job_id)
            status = status_data["status"]

            if status == "completed":
                return status_data
            elif status == "failed":
                raise Exception(f"Job failed: {status_data.get('error')}")

            time.sleep(poll_interval)

        raise TimeoutError(f"Job did not complete within {timeout}s")

# Usage example
if __name__ == "__main__":
    client = BenchmarkClient()

    # Submit benchmark
    print("Submitting benchmark job...")
    result = client.submit_benchmark(
        dataset_type="cryoet",
        shape=[256, 256, 256],
        voxel_size=[2.5, 2.5, 2.5],
        compression_profile="balanced"
    )

    job_id = result["job_id"]
    print(f"Job submitted: {job_id}")

    # Wait for completion
    print("Waiting for completion...")
    final_result = client.wait_for_completion(job_id)

    # Print results
    print("\nBenchmark Results:")
    print(json.dumps(final_result["results"], indent=2))
```

See `example_pipeline_client.py` for a complete working example.

---

## Pipeline Integration Examples

### 1. CryoET Data Portal Integration

```python
from cryoet_portal import Client
from benchmark_client import BenchmarkClient

# Download tomogram from portal
portal = Client()
dataset = portal.get_dataset(10445)
tomogram = dataset.tomograms[0]

# Download data
data = tomogram.download()

# Submit benchmark
bench_client = BenchmarkClient()
result = bench_client.submit_benchmark(
    dataset_type="cryoet",
    shape=data.shape,
    voxel_size=tomogram.voxel_spacing,
    compression_profile="archival"
)

print(f"Benchmark job: {result['job_id']}")
```

### 2. Light Sheet Pipeline Integration

```python
def process_lightsheet_acquisition(image_path):
    """Process new light sheet image."""
    import tifffile

    # Load image
    img = tifffile.imread(image_path)

    # Submit benchmark automatically
    client = BenchmarkClient()
    result = client.submit_benchmark(
        dataset_type="light_sheet",
        shape=img.shape,
        voxel_size=[0.4, 0.16, 0.16],  # z, y, x in microns
        compression_profile="balanced"
    )

    # Store job ID for tracking
    return result["job_id"]
```

### 3. Webhook Callback Integration

```python
# Configure webhook server to POST results
import aiohttp

async def on_benchmark_complete(job_id, results):
    """Called when benchmark completes."""
    async with aiohttp.ClientSession() as session:
        await session.post(
            "https://your-pipeline.com/benchmark-complete",
            json={
                "job_id": job_id,
                "results": results
            }
        )
```

---

## Configuration

### Server Configuration

Edit `benchmark_webhook_server.py`:

```python
# Server settings
DEFAULT_PORT = 8080
MAX_CONCURRENT_JOBS = 4
JOB_TIMEOUT = 3600  # seconds

# Benchmark settings
DEFAULT_COMPRESSION_PROFILE = "balanced"
SUPPORTED_CODECS = ["blosc_zstd", "blosc_lz4", "zstd", "gzip"]
```

### Environment Variables

```bash
# Set environment variables
export BENCHMARK_SERVER_PORT=8080
export BENCHMARK_MAX_JOBS=4
export BENCHMARK_DATA_DIR=/path/to/data
```

---

## Testing

### Quick Test

```bash
# Run quick test suite
python test_webhook_quick.py
```

### Manual Testing

```bash
# Terminal 1: Start server
python benchmark_webhook_server.py

# Terminal 2: Submit test job
curl -X POST http://localhost:8080/benchmark \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_type": "synthetic",
    "shape": [128, 128, 128],
    "compression_profile": "fast"
  }'

# Check status
curl http://localhost:8080/status/<job_id>

# Check health
curl http://localhost:8080/health
```

---

## Production Deployment

### Using systemd

Create `/etc/systemd/system/zarr-benchmark-server.service`:

```ini
[Unit]
Description=Zarr Benchmark Webhook Server
After=network.target

[Service]
Type=simple
User=benchmark
WorkingDirectory=/opt/zarr-benchmarks
ExecStart=/opt/zarr-benchmarks/venv/bin/python benchmark_webhook_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable zarr-benchmark-server
sudo systemctl start zarr-benchmark-server
sudo systemctl status zarr-benchmark-server
```

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements-cryoet.txt .
RUN pip install -r requirements-cryoet.txt && pip install aiohttp

COPY . .

EXPOSE 8080

CMD ["python", "benchmark_webhook_server.py"]
```

Build and run:
```bash
docker build -t zarr-benchmark-server .
docker run -d -p 8080:8080 --name benchmark-server zarr-benchmark-server
```

### Using Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name benchmark.example.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Security Considerations

### Authentication (Recommended for Production)

```python
# Add API key authentication
API_KEY = os.environ.get("BENCHMARK_API_KEY")

@routes.post('/benchmark')
async def submit_benchmark(request):
    # Check API key
    auth_header = request.headers.get("Authorization")
    if not auth_header or auth_header != f"Bearer {API_KEY}":
        return web.json_response(
            {"error": "Unauthorized"},
            status=401
        )

    # Process request...
```

### Rate Limiting

```python
from aiohttp_ratelimit import RateLimiter

# Add rate limiting
rate_limiter = RateLimiter(
    max_requests=10,
    time_window=60  # 10 requests per minute
)

app.middlewares.append(rate_limiter)
```

### Input Validation

```python
# Validate input sizes
MAX_VOLUME_SIZE = 1024 ** 3  # 1GB

def validate_shape(shape):
    volume_size = np.prod(shape) * 4  # float32
    if volume_size > MAX_VOLUME_SIZE:
        raise ValueError(f"Volume too large: {volume_size} bytes")
```

---

## Troubleshooting

### Server Won't Start

```bash
# Check if port is in use
lsof -i :8080

# Try different port
python benchmark_webhook_server.py --port 8888
```

### Jobs Stuck in Pending

```bash
# Check server logs
tail -f benchmark_server.log

# Restart server
pkill -f benchmark_webhook_server.py
python benchmark_webhook_server.py
```

### Out of Memory

```python
# Reduce concurrent jobs
MAX_CONCURRENT_JOBS = 2

# Use smaller test volumes
MAX_VOLUME_SIZE = 256 ** 3  # 64MB
```

---

## Performance Optimization

### Caching Results

```python
# Cache common benchmark configurations
RESULT_CACHE = {}

def get_cached_result(config_hash):
    return RESULT_CACHE.get(config_hash)
```

### Parallel Processing

```python
# Use multiprocessing for CPU-bound tasks
from multiprocessing import Pool

with Pool(processes=4) as pool:
    results = pool.map(run_benchmark, jobs)
```

---

## Monitoring & Logging

### Enable Detailed Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('benchmark_server.log'),
        logging.StreamHandler()
    ]
)
```

### Metrics Collection

```python
# Track metrics
METRICS = {
    "total_jobs": 0,
    "completed_jobs": 0,
    "failed_jobs": 0,
    "avg_completion_time": 0.0
}

@routes.get('/metrics')
async def get_metrics(request):
    return web.json_response(METRICS)
```

---

## Further Reading

- **Main Documentation**: `README_CRYOET_EXTENSION.md`
- **Technical Report**: `TECHNICAL_REPORT.md`
- **Contributing**: `CONTRIBUTING.md`
- **Example Client**: `example_pipeline_client.py`
- **Server Code**: `benchmark_webhook_server.py`

---

## Support

- **Issues**: https://github.com/MaadhavKothari/zarr-benchmarks-cryoet/issues
- **Discussions**: https://github.com/MaadhavKothari/zarr-benchmarks-cryoet/discussions

---

**Version History:**
- v1.0.0 (2025-11-18): Initial webhook server release
