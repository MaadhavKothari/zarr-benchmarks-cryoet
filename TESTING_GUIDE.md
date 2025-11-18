# Testing Guide: Zarr Benchmarks with Synthetic & Real Data

## 🎯 Overview

This repository now supports comprehensive benchmarking on both **synthetic test
data** (fast, no downloads) and **real CryoET data** (production validation).

---

## 🚀 Quick Start: Synthetic Data Tests

### Fast Automated Test Suite (~1.2 seconds)

Perfect for CI/CD, quick validation, and demos:

```bash
# Run full test suite
python test_benchmarks_synthetic.py

# Output: 4 test categories, 16 tests total
# - Compression codecs (6 codecs including gzip)
# - Zarr v2 vs v3
# - Chunking strategies
# - Data integrity with comprehensive metrics
```

**Results saved to:** `data/output/test_synthetic/`

### Codecs Tested

- ✅ **blosc_zstd** - Best compression (1.21×)
- ✅ **blosc_lz4** - Fastest write (0.009s)
- ✅ **blosc_zlib** - Highest compression (1.23×)
- ✅ **zstd** - Good balance
- ✅ **gzip** - Compatibility standard
- ✅ **no_compression** - Baseline

### Comprehensive Metrics

All tests include:

- **SSIM** (Structural Similarity Index)
- **PSNR** (Peak Signal-to-Noise Ratio)
- **MSE** (Mean Squared Error)
- **MAE** (Mean Absolute Error)
- **Max Error** (Maximum pixel difference)
- **Correlation** (Pearson correlation coefficient)
- **Exact Match** (Lossless verification)

---

## 📊 Synthetic Data Patterns

Generate different test patterns for specific scenarios:

```python
from test_data_generator import generate_synthetic_volume, get_test_dataset_info

# Realistic microscopy simulation (default)
data = generate_synthetic_volume(size=128, pattern='realistic')

# Other patterns:
# - 'noise': High entropy (worst-case compression)
# - 'gradient': Low entropy (best-case compression)
# - 'spheres': Structured data (segmentation-like)
# - 'realistic': Simulated microscopy (most realistic)
```

### When to Use Each Pattern

| Pattern       | Compressibility | Use Case                           |
| ------------- | --------------- | ---------------------------------- |
| **noise**     | Poor            | Stress test compression algorithms |
| **gradient**  | Excellent       | Best-case compression scenarios    |
| **spheres**   | Good            | Segmentation/label data testing    |
| **realistic** | Moderate        | Realistic benchmarking             |

---

## 🔬 Real CryoET Data Tests

### Notebooks (Interactive)

#### 1. Comprehensive Benchmark

```bash
jupyter lab comprehensive_cryoet_notebook.ipynb
```

- Downloads real CryoET data (Dataset 10445)
- Tests 4-6 compression codecs
- Runtime: ~5-10 minutes
- Results: Blosc-Zstd achieves 1.19× compression

#### 2. Zarr v2 vs v3 Comparison

```bash
jupyter lab zarr_v2_v3_comparison.ipynb
```

- Side-by-side v2 and v3 testing
- Performance and file count analysis
- Runtime: ~5-10 minutes

#### 3. iohub Format Conversion

```bash
jupyter lab iohub_conversion_benchmark.ipynb
```

- Tests TIFF ↔ OME-Zarr conversion
- 5 conversion paths
- Legacy data migration validation
- Runtime: ~5-15 minutes

#### 4. Advanced Compression Matrix

```bash
jupyter lab advanced_compression_matrix.ipynb
```

- Heat maps and Pareto frontier analysis
- 100-150 configurations tested
- Runtime: ~30-60 minutes

#### 5. QC & Benchmarking Tool

```bash
jupyter lab cryoet_qc_benchmark_tool.ipynb
```

- PixelPatrol-inspired quality control
- 7 comprehensive QC checks
- Integrated with benchmarking

### Python Scripts (CLI)

#### Quick Test (30 seconds)

```bash
python cryoet_real_data_quick.py
```

#### Comprehensive Chunking Benchmark (5 minutes)

```bash
python cryoet_chunking_benchmark.py
```

#### Advanced Multi-Run Benchmark

```bash
python cryoet_advanced_benchmark.py
```

---

## 🔧 Integration Examples

### CI/CD Pipeline

```yaml
# .github/workflows/test-benchmarks.yml
name: Zarr Benchmarks Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.13"
      - name: Install dependencies
        run: pip install -r requirements-cryoet.txt
      - name: Run synthetic benchmarks
        run: python test_benchmarks_synthetic.py
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
python test_benchmarks_synthetic.py
if [ $? -ne 0 ]; then
    echo "Benchmark tests failed!"
    exit 1
fi
```

---

## 📈 Performance Expectations

### Synthetic Data (128³ volume, 8 MB)

| Test Category       | Tests  | Runtime   |
| ------------------- | ------ | --------- |
| Compression Codecs  | 6      | ~0.5s     |
| Zarr Versions       | 2      | ~0.1s     |
| Chunking Strategies | 3      | ~0.3s     |
| Data Integrity      | 5      | ~0.3s     |
| **Total**           | **16** | **~1.2s** |

### Real CryoET Data (256³ volume, 64 MB)

| Task             | Runtime   |
| ---------------- | --------- |
| Download from S3 | ~60s      |
| Quick benchmark  | ~30s      |
| Comprehensive    | ~5-10min  |
| Advanced matrix  | ~30-60min |

---

## 🎓 Best Practices

### For Development

1. Use **synthetic tests** for quick validation
2. Test with `realistic` pattern for most accurate results
3. Run full suite before committing

### For Production

1. Validate on **real CryoET data** first
2. Test multiple datasets for robustness
3. Compare against your existing pipeline

### For Research

1. Use **advanced compression matrix** for thorough analysis
2. Include **QC checks** before compression
3. Document results in `GALLERY.md`

---

## 🐛 Troubleshooting

### Zarr v3 Tests Failing

```python
# Ensure experimental API is enabled
import os
os.environ['ZARR_V3_EXPERIMENTAL_API'] = '1'
```

### iohub Import Errors

```bash
pip install iohub>=0.2.2
```

### Slow Downloads

```python
# Use smaller download size
DOWNLOAD_SIZE = 128  # Instead of 256 or 512
```

### Memory Issues

```python
# Generate smaller synthetic volumes
data = generate_synthetic_volume(size=64)  # Instead of 128 or 256
```

---

## 📁 Output Structure

```
data/output/
├── test_synthetic/           # Synthetic test results
│   ├── compression_results.csv
│   ├── versions_results.csv
│   ├── chunking_results.csv
│   └── integrity_results.csv
│
├── comprehensive_benchmark/   # Real CryoET comprehensive
│   ├── benchmark_results_256cube.csv
│   ├── benchmark_comparison_256cube.png
│   └── *.zarr/               # Test stores
│
├── v2_v3_comparison/         # Version comparison
│   ├── v2_v3_comparison_results.csv
│   ├── v2_v3_comparison.png
│   └── *.zarr/
│
├── iohub_conversion/         # Format conversion
│   ├── conversion_benchmark_results.csv
│   ├── conversion_benchmark.png
│   └── *.zarr/
│
└── chunking_benchmarks/      # Chunking analysis
    ├── chunking_results.csv
    ├── chunking_comparison.png
    └── chunks_*.zarr/
```

---

## ✅ Quality Assurance

All tests verify:

- ✓ Lossless compression (exact data match)
- ✓ Image quality metrics (SSIM ≥ 0.9999)
- ✓ Performance benchmarks
- ✓ File integrity
- ✓ Metadata preservation

---

## 📚 Further Reading

- **TECHNICAL_REPORT.md** - Detailed compression analysis
- **CHUNKING_SHARDING_REPORT.md** - Chunking strategies
- **EXECUTIVE_SUMMARY.md** - Quick reference
- **LOCAL_REVIEW.md** - Current status and results

---

## 🔗 Resources

- **HEFTIE Project:** <https://heftieproject.github.io/zarr-benchmarks/>
- **CryoET Portal:** <https://cryoetdataportal.czscience.com/>
- **iohub:** <https://github.com/czbiohub-sf/iohub>
- **Zarr:** <https://zarr.readthedocs.io/>
- **OME-NGFF:** <https://ngff.openmicroscopy.org/>

---

_Last updated: November 14, 2025_
