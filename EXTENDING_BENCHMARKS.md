# Extending the Benchmark Suite

This guide shows you how to add new benchmark types to the zarr-benchmarks system.

## Architecture Overview

The system has three main extension points:

1. **Dataset Types** - Add new imaging modalities or data types
2. **Benchmark Configurations** - Define what to test and how
3. **Integration Points** - Connect to pipelines via webhook or direct API

---

## Extension Point 1: Adding New Dataset Types

### Current Supported Types

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

### Example 1: Adding MRI Dataset Type

**File**: `src/zarr_benchmarks/dataset_types.py`

```python
class DatasetType(Enum):
    # ... existing types ...
    MRI = "mri"  # Magnetic Resonance Imaging
    CT_SCAN = "ct_scan"  # Computed Tomography
    PET_SCAN = "pet_scan"  # Positron Emission Tomography
```

**Create helper function**:

```python
def create_mri_metadata(
    shape: Tuple[int, int, int, int],  # TZYX or sequences
    voxel_size: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    source: str = "unknown",
) -> DatasetMetadata:
    """Helper to create MRI dataset metadata"""
    return DatasetMetadata(
        name=f"mri_{shape[1]}x{shape[2]}x{shape[3]}",
        dataset_type=DatasetType.MRI,
        shape=shape,
        dtype=np.dtype(np.float32),  # MRI typically float32
        voxel_size=voxel_size,
        units="mm",
        timepoints=shape[0],
        source=source,
        modality_specific={
            "field_strength": "3T",  # Tesla
            "sequence": "T1-weighted",
            "echo_time": 30,  # ms
            "repetition_time": 2000,  # ms
        },
    )
```

**Update compression recommendations**:

```python
def suggest_compression(self) -> str:
    """Suggest best compression codec based on dataset type"""
    recommendations = {
        # ... existing ...
        DatasetType.MRI: "blosc_zstd",  # Good for medical imaging
        DatasetType.CT_SCAN: "blosc_zstd",
        DatasetType.PET_SCAN: "blosc_lz4",  # Fast for clinical use
    }
    return recommendations.get(self.dataset_type, "blosc_zstd")
```

---

## Extension Point 2: Custom Benchmark Scripts

### Example 2: Creating an MRI Benchmark Script

**File**: `mri_benchmark.py`

```python
#!/usr/bin/env python3
"""
MRI Zarr Benchmarking
Specialized benchmarks for medical imaging data
"""

import numpy as np
from pathlib import Path

from zarr_benchmarks.dataset_types import (
    create_mri_metadata,
    BenchmarkConfig,
    CompressionProfile,
    DatasetType,
)
from multi_dataset_benchmark import DatasetBenchmarkRunner

def generate_mri_data(shape):
    """Generate realistic MRI-like data"""
    # Simulate T1-weighted brain MRI
    data = np.random.randn(*shape).astype(np.float32)

    # Add brain-like structure (sphere with intensity gradient)
    center = [s // 2 for s in shape]
    z, y, x = np.ogrid[:shape[0], :shape[1], :shape[2]]
    radius = min(shape) // 3
    brain_mask = ((z - center[0])**2 +
                  (y - center[1])**2 +
                  (x - center[2])**2) < radius**2

    data[brain_mask] += 1000  # Tissue signal
    data = np.clip(data, 0, 4095)  # Realistic MRI range

    return data

def main():
    print("=" * 70)
    print("MRI ZARR BENCHMARKING")
    print("=" * 70)

    # Generate synthetic MRI data
    shape = (10, 256, 256, 256)  # 10 timepoints, 256^3 voxels
    print(f"\nGenerating MRI data: {shape}")
    data = generate_mri_data(shape[1:])  # Single timepoint for testing

    # Create metadata
    metadata = create_mri_metadata(
        shape=(1, *data.shape),
        voxel_size=(1.0, 1.0, 1.0),  # 1mm isotropic
        source="synthetic_brain",
    )

    print(f"Dataset: {metadata.name}")
    print(f"Size: {metadata.total_size_mb:.2f} MB")
    print(f"Suggested compression: {metadata.suggest_compression()}")
    print(f"Suggested chunks: {metadata.suggest_chunk_size()}")

    # Test different compression profiles
    profiles = [
        CompressionProfile.ARCHIVAL,  # Maximum compression
        CompressionProfile.BALANCED,  # Clinical use
        CompressionProfile.FAST,      # Real-time viewing
    ]

    for profile in profiles:
        print(f"\n{'='*70}")
        print(f"Testing Profile: {profile.value}")
        print('='*70)

        config = BenchmarkConfig(
            dataset_metadata=metadata,
            compression_profile=profile,
            codecs_to_test=["blosc_zstd", "blosc_lz4", "zstd"],
            num_runs=3,
            output_dir=f"data/output/mri_benchmarks/{profile.value}",
        )

        runner = DatasetBenchmarkRunner(config)
        results = runner.run(data)

        print(f"\nResults for {profile.value}:")
        print(f"  Best write: {results['best_write']['codec']} "
              f"({results['best_write']['time_s']:.3f}s)")
        print(f"  Best read: {results['best_read']['codec']} "
              f"({results['best_read']['time_s']:.3f}s)")
        print(f"  Best compression: {results['best_compression']['codec']} "
              f"({results['best_compression']['ratio']:.2f}×)")

if __name__ == "__main__":
    main()
```

**Run it**:

```bash
chmod +x mri_benchmark.py
python mri_benchmark.py
```

---

## Extension Point 3: Webhook Integration

### Example 3: Integrating with an MRI Pipeline

**Pipeline-side code**:

```python
#!/usr/bin/env python3
"""
MRI Pipeline Integration
Automatically benchmark new MRI scans as they arrive
"""

import requests
import time
from pathlib import Path

def submit_mri_benchmark(scan_path: Path, webhook_url: str):
    """Submit MRI scan for benchmarking"""

    # Load scan metadata
    # (In real code, read from DICOM/NIfTI headers)
    shape = (1, 256, 256, 256)
    voxel_size = [1.0, 1.0, 1.0]

    # Submit benchmark request
    payload = {
        "dataset": {
            "name": f"mri_scan_{scan_path.stem}",
            "type": "mri",
            "shape": shape,
            "dtype": "float32",
            "voxel_size": voxel_size,
        },
        "benchmark": {
            "codecs": ["blosc_zstd", "blosc_lz4"],
            "compression_profile": "balanced",
            "num_runs": 3,
        },
    }

    response = requests.post(
        f"{webhook_url}/webhook/benchmark",
        json=payload
    )

    if response.status_code == 202:
        job_info = response.json()
        print(f"✓ Benchmark submitted: {job_info['job_id']}")
        return job_info['job_id']
    else:
        print(f"✗ Error: {response.status_code}")
        return None

def wait_for_results(job_id: str, webhook_url: str, timeout: int = 300):
    """Poll for benchmark results"""
    start = time.time()

    while time.time() - start < timeout:
        response = requests.get(f"{webhook_url}/status/{job_id}")
        status = response.json()

        if status['status'] == 'completed':
            return status['results']
        elif status['status'] == 'failed':
            raise Exception(f"Benchmark failed: {status.get('error')}")

        time.sleep(5)

    raise TimeoutError("Benchmark timed out")

# Example usage
if __name__ == "__main__":
    webhook_url = "http://localhost:8080"
    scan_path = Path("/path/to/patient_001_brain.nii.gz")

    # Submit benchmark
    job_id = submit_mri_benchmark(scan_path, webhook_url)

    if job_id:
        # Wait for results
        print("Waiting for results...")
        results = wait_for_results(job_id, webhook_url)

        print("\nBenchmark Results:")
        print(f"  Recommended codec: {results['best_compression']['codec']}")
        print(f"  Compression ratio: {results['best_compression']['ratio']:.2f}×")
        print(f"  Size reduction: {(1 - 1/results['best_compression']['ratio']) * 100:.1f}%")
```

---

## Extension Point 4: Adding New Metrics

### Example 4: Medical Imaging Quality Metrics

**File**: `src/zarr_benchmarks/quality_metrics.py` (create new)

```python
"""
Extended Quality Metrics for Specialized Domains
"""

import numpy as np
from typing import Dict, Any

def calculate_cnr(
    original: np.ndarray,
    compressed: np.ndarray,
    roi_mask: np.ndarray,
    background_mask: np.ndarray
) -> float:
    """
    Calculate Contrast-to-Noise Ratio (CNR)
    Important for medical imaging

    CNR = |mean_roi - mean_bg| / std_bg
    """
    mean_roi = np.mean(compressed[roi_mask])
    mean_bg = np.mean(compressed[background_mask])
    std_bg = np.std(compressed[background_mask])

    return abs(mean_roi - mean_bg) / std_bg if std_bg > 0 else 0

def calculate_snr(image: np.ndarray, roi_mask: np.ndarray) -> float:
    """
    Calculate Signal-to-Noise Ratio (SNR)
    SNR = mean_signal / std_noise
    """
    signal = np.mean(image[roi_mask])
    noise = np.std(image[~roi_mask])

    return signal / noise if noise > 0 else np.inf

def medical_imaging_metrics(
    original: np.ndarray,
    compressed: np.ndarray,
    metadata: Dict[str, Any]
) -> Dict[str, float]:
    """
    Calculate medical imaging specific metrics
    """
    from skimage.metrics import structural_similarity as ssim
    from skimage.metrics import peak_signal_noise_ratio as psnr

    # Standard metrics
    metrics = {
        'ssim': ssim(original, compressed, data_range=original.max()),
        'psnr': psnr(original, compressed, data_range=original.max()),
        'mse': np.mean((original - compressed) ** 2),
        'mae': np.mean(np.abs(original - compressed)),
    }

    # Medical-specific metrics
    if 'roi_mask' in metadata:
        roi_mask = metadata['roi_mask']
        bg_mask = ~roi_mask

        metrics['cnr'] = calculate_cnr(original, compressed, roi_mask, bg_mask)
        metrics['snr'] = calculate_snr(compressed, roi_mask)

    return metrics
```

---

## Extension Point 5: Custom Analysis Workflows

### Example 5: Batch Processing Multiple Datasets

**File**: `batch_benchmark_pipeline.py`

```python
#!/usr/bin/env python3
"""
Batch Benchmarking Pipeline
Process multiple datasets from different modalities
"""

import asyncio
import aiohttp
from pathlib import Path
from typing import List, Dict
import pandas as pd

class BatchBenchmarkPipeline:
    """Orchestrate benchmarks across multiple datasets"""

    def __init__(self, webhook_url: str = "http://localhost:8080"):
        self.webhook_url = webhook_url
        self.results = []

    async def submit_job(self, session: aiohttp.ClientSession,
                         dataset_config: Dict) -> str:
        """Submit a single benchmark job"""
        async with session.post(
            f"{self.webhook_url}/webhook/benchmark",
            json=dataset_config
        ) as response:
            result = await response.json()
            return result['job_id']

    async def check_status(self, session: aiohttp.ClientSession,
                          job_id: str) -> Dict:
        """Check job status"""
        async with session.get(
            f"{self.webhook_url}/status/{job_id}"
        ) as response:
            return await response.json()

    async def process_dataset(self, session: aiohttp.ClientSession,
                             dataset_config: Dict):
        """Process a single dataset"""
        print(f"Submitting: {dataset_config['dataset']['name']}")

        # Submit
        job_id = await self.submit_job(session, dataset_config)

        # Poll until complete
        while True:
            status = await self.check_status(session, job_id)

            if status['status'] == 'completed':
                print(f"✓ Completed: {dataset_config['dataset']['name']}")
                self.results.append({
                    'dataset': dataset_config['dataset']['name'],
                    'type': dataset_config['dataset']['type'],
                    **status['results']
                })
                break
            elif status['status'] == 'failed':
                print(f"✗ Failed: {dataset_config['dataset']['name']}")
                break

            await asyncio.sleep(2)

    async def run_batch(self, datasets: List[Dict]):
        """Process multiple datasets in parallel"""
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.process_dataset(session, ds)
                for ds in datasets
            ]
            await asyncio.gather(*tasks)

        # Save summary
        df = pd.DataFrame(self.results)
        df.to_csv('batch_benchmark_results.csv', index=False)
        print(f"\n✓ Saved results for {len(self.results)} datasets")
        return df

# Example usage
async def main():
    pipeline = BatchBenchmarkPipeline()

    # Define datasets to benchmark
    datasets = [
        {
            "dataset": {
                "name": "cryoet_sample_1",
                "type": "cryoet",
                "shape": [128, 128, 128],
                "dtype": "float32",
                "voxel_size": [13.48, 13.48, 13.48],
            },
            "benchmark": {
                "codecs": ["blosc_zstd", "blosc_lz4"],
                "compression_profile": "balanced",
                "num_runs": 2,
            },
        },
        {
            "dataset": {
                "name": "lightsheet_embryo_1",
                "type": "light_sheet",
                "shape": [10, 512, 512, 512],
                "dtype": "uint16",
                "voxel_size": [2.0, 0.4, 0.4],
            },
            "benchmark": {
                "codecs": ["blosc_zstd", "blosc_lz4"],
                "compression_profile": "fast",
                "num_runs": 2,
            },
        },
        {
            "dataset": {
                "name": "confocal_cells_1",
                "type": "confocal",
                "shape": [1, 3, 256, 1024, 1024],
                "dtype": "uint16",
                "voxel_size": [0.5, 0.1, 0.1],
            },
            "benchmark": {
                "codecs": ["blosc_lz4", "zstd"],
                "compression_profile": "balanced",
                "num_runs": 2,
            },
        },
    ]

    # Run batch processing
    results = await pipeline.run_batch(datasets)

    # Print summary
    print("\n" + "="*70)
    print("BATCH BENCHMARK SUMMARY")
    print("="*70)
    print(results[['dataset', 'type', 'best_compression']].to_string())

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Extension Point 6: Domain-Specific Optimizations

### Example 6: Astronomy Data (FITS files)

```python
#!/usr/bin/env python3
"""
Astronomy/FITS Data Benchmarking
Specialized for radio/optical telescope data
"""

from astropy.io import fits
from zarr_benchmarks.dataset_types import DatasetType, DatasetMetadata
import numpy as np

class DatasetType(Enum):
    # ... existing types ...
    FITS_RADIO = "fits_radio"     # Radio telescope
    FITS_OPTICAL = "fits_optical"  # Optical telescope
    FITS_XRAY = "fits_xray"        # X-ray telescope

def create_fits_metadata(
    fits_path: str,
    dataset_type: DatasetType = DatasetType.FITS_OPTICAL
) -> DatasetMetadata:
    """Create metadata from FITS file"""
    with fits.open(fits_path) as hdul:
        header = hdul[0].header
        data = hdul[0].data

        return DatasetMetadata(
            name=f"fits_{fits_path.stem}",
            dataset_type=dataset_type,
            shape=data.shape,
            dtype=data.dtype,
            voxel_size=None,  # FITS uses WCS
            units="counts",
            source=header.get('TELESCOP', 'unknown'),
            modality_specific={
                'instrument': header.get('INSTRUME'),
                'filter': header.get('FILTER'),
                'exposure': header.get('EXPTIME'),
                'wcs': extract_wcs(header),  # World Coordinate System
            }
        )

def suggest_compression_for_astronomy(data_type: str) -> str:
    """Astronomy-specific compression recommendations"""
    recommendations = {
        'radio': 'blosc_zstd',  # Often float32, good compression
        'optical': 'blosc_lz4',  # Integer counts, fast access
        'spectral': 'blosc_zstd',  # 3D datacubes, prioritize compression
    }
    return recommendations.get(data_type, 'blosc_zstd')
```

---

## Quick Reference: Adding a New Benchmark

### 5-Step Process

1. **Define the dataset type** in `dataset_types.py`:

   ```python
   MYNEW_TYPE = "mynew_type"
   ```

2. **Create metadata helper**:

   ```python
   def create_mynew_metadata(...) -> DatasetMetadata:
       return DatasetMetadata(...)
   ```

3. **Add compression recommendation**:

   ```python
   DatasetType.MYNEW_TYPE: "blosc_zstd"  # or appropriate codec
   ```

4. **Create benchmark script**:

   ```python
   # mynew_benchmark.py
   from zarr_benchmarks.dataset_types import create_mynew_metadata
   from multi_dataset_benchmark import DatasetBenchmarkRunner
   ```

5. **Test via webhook or direct**:
   ```bash
   python mynew_benchmark.py
   # or
   curl -X POST http://localhost:8080/webhook/benchmark ...
   ```

---

## Integration Patterns

### Pattern 1: Direct Python API

```python
from zarr_benchmarks.dataset_types import *
from multi_dataset_benchmark import DatasetBenchmarkRunner

# Create config
config = BenchmarkConfig(...)
runner = DatasetBenchmarkRunner(config)

# Run
results = runner.run(my_data)
```

### Pattern 2: Webhook/REST API

```python
import requests

response = requests.post(
    "http://localhost:8080/webhook/benchmark",
    json={...}
)
job_id = response.json()['job_id']
```

### Pattern 3: CLI Tool

```bash
python multi_dataset_benchmark.py \
  --dataset-type cryoet \
  --shape 256,256,256 \
  --codecs blosc_zstd blosc_lz4 \
  --profile balanced
```

---

## Best Practices

1. **Always validate data**: Check shape, dtype, ranges
2. **Use appropriate dtypes**: uint8/16 for microscopy, float32 for EM/MRI
3. **Test chunk sizes**: Start with suggested, then optimize
4. **Profile-specific tuning**: Different use cases need different settings
5. **Document your extensions**: Add to this guide!
6. **Consider metadata**: Store important experimental parameters

---

## Testing Your Extension

```python
def test_mynew_dataset():
    """Test new dataset type"""
    metadata = create_mynew_metadata(...)

    assert metadata.dataset_type == DatasetType.MYNEW_TYPE
    assert metadata.suggest_compression() in VALID_CODECS
    assert all(c > 0 for c in metadata.suggest_chunk_size())

    print("✓ Metadata validation passed")
```

---

## Contributing

To contribute your extensions back to the project:

1. Add your dataset type to `dataset_types.py`
2. Create example benchmark script
3. Add documentation to this guide
4. Submit a pull request

---

## Resources

- **Main Documentation**: `README_CRYOET_EXTENSION.md`
- **Webhook API**: `WEBHOOK_API_GUIDE.md`
- **Dataset Types**: `src/zarr_benchmarks/dataset_types.py`
- **Multi-Dataset Runner**: `multi_dataset_benchmark.py`
- **Examples**: All `*_benchmark.py` files

---

**Questions?** Open an issue on GitHub or check the documentation!
