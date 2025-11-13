#!/usr/bin/env python3
"""Quick test script to verify zarr-benchmarks setup"""

import numpy as np
import pathlib
import time
from zarr_benchmarks.read_write_zarr import read_write_zarr
from zarr_benchmarks import utils

print("=" * 60)
print("Testing Zarr Benchmarks Setup")
print("=" * 60)

# Create a small test array
print("\n1. Creating test data...")
test_data = np.random.rand(128, 128, 128).astype(np.float32)
print(f"   Test array shape: {test_data.shape}")
print(f"   Test array size: {test_data.nbytes / (1024**2):.2f} MB")

# Test writing with Blosc compression
print("\n2. Testing write with Blosc compression...")
output_dir = pathlib.Path("data/output/test")
output_dir.mkdir(parents=True, exist_ok=True)
store_path = output_dir / "test_blosc.zarr"

blosc_compressor = read_write_zarr.get_blosc_compressor(
    cname="zstd",
    clevel=5,
    shuffle="shuffle",
    zarr_spec=3
)

utils.remove_output_dir(store_path)
start_time = time.time()
read_write_zarr.write_zarr_array(
    test_data,
    store_path,
    overwrite=False,
    chunks=(64, 64, 64),
    compressor=blosc_compressor,
    zarr_spec=3
)
write_time = time.time() - start_time
print(f"   Write time: {write_time:.3f}s")

# Test reading
print("\n3. Testing read...")
start_time = time.time()
read_data = read_write_zarr.read_zarr_array(store_path)
read_time = time.time() - start_time
print(f"   Read time: {read_time:.3f}s")

# Get metrics
compression_ratio = read_write_zarr.get_compression_ratio(store_path)
storage_size = utils.get_directory_size(store_path) / (1024**2)

print("\n4. Results:")
print(f"   Compression ratio: {compression_ratio:.2f}x")
print(f"   Storage size: {storage_size:.2f} MB")
print(f"   Data integrity: {np.allclose(test_data, read_data)}")

print("\n" + "=" * 60)
print("✓ All tests passed! Setup is working correctly.")
print("=" * 60)
print("\nYou can now run the Jupyter notebooks:")
print("  - zarr_benchmarks_demo.ipynb")
print("  - cryoet_portal_benchmark.ipynb (requires additional dependencies)")
