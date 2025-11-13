#!/usr/bin/env python3
"""
Standalone Zarr Benchmarks Demo Script
This script runs all the benchmarks from the notebook in a simple Python script.
"""

import numpy as np
import pathlib
import time
import pandas as pd
import matplotlib.pyplot as plt
from zarr_benchmarks.read_write_zarr import read_write_zarr
from zarr_benchmarks import utils

print("=" * 70)
print("ZARR BENCHMARKS DEMO")
print("=" * 70)

# ============================================================================
# 1. CREATE SAMPLE 3D DATA
# ============================================================================
print("\n📊 1. Creating sample 3D data...")
image_size = 256
sample_image = np.random.rand(image_size, image_size, image_size).astype(np.float32)

print(f"   Sample image shape: {sample_image.shape}")
print(f"   Sample image dtype: {sample_image.dtype}")
print(f"   Uncompressed size: {sample_image.nbytes / (1024**2):.2f} MB")

# ============================================================================
# 2. SETUP BENCHMARK PARAMETERS
# ============================================================================
print("\n⚙️  2. Setting up benchmark parameters...")
output_dir = pathlib.Path("data/output/demo_benchmarks")
output_dir.mkdir(parents=True, exist_ok=True)

chunk_size = 64
chunks = (chunk_size, chunk_size, chunk_size)
zarr_spec = 3

results = {}
print(f"   Chunk size: {chunk_size}x{chunk_size}x{chunk_size}")
print(f"   Zarr spec: v{zarr_spec}")

# ============================================================================
# 3. TEST BLOSC COMPRESSION
# ============================================================================
print("\n🔧 3. Testing Blosc Compression...")
store_path = output_dir / "blosc_compressed.zarr"
blosc_compressor = read_write_zarr.get_blosc_compressor(
    cname="zstd",
    clevel=5,
    shuffle="shuffle",
    zarr_spec=zarr_spec
)

utils.remove_output_dir(store_path)
start_time = time.time()
read_write_zarr.write_zarr_array(
    sample_image,
    store_path,
    overwrite=False,
    chunks=chunks,
    compressor=blosc_compressor,
    zarr_spec=zarr_spec
)
write_time = time.time() - start_time

start_time = time.time()
read_image = read_write_zarr.read_zarr_array(store_path)
read_time = time.time() - start_time

compression_ratio = read_write_zarr.get_compression_ratio(store_path)
storage_size = utils.get_directory_size(store_path) / (1024**2)

results['blosc'] = {
    'write_time': write_time,
    'read_time': read_time,
    'compression_ratio': compression_ratio,
    'storage_size_mb': storage_size
}

print(f"   ✓ Write time: {write_time:.3f}s")
print(f"   ✓ Read time: {read_time:.3f}s")
print(f"   ✓ Compression ratio: {compression_ratio:.2f}x")
print(f"   ✓ Storage size: {storage_size:.2f} MB")
print(f"   ✓ Data integrity: {np.allclose(sample_image, read_image)}")

# ============================================================================
# 4. TEST GZIP COMPRESSION
# ============================================================================
print("\n🔧 4. Testing GZip Compression...")
store_path = output_dir / "gzip_compressed.zarr"
gzip_compressor = read_write_zarr.get_gzip_compressor(
    level=6,
    zarr_spec=zarr_spec
)

utils.remove_output_dir(store_path)
start_time = time.time()
read_write_zarr.write_zarr_array(
    sample_image,
    store_path,
    overwrite=False,
    chunks=chunks,
    compressor=gzip_compressor,
    zarr_spec=zarr_spec
)
write_time = time.time() - start_time

start_time = time.time()
read_image = read_write_zarr.read_zarr_array(store_path)
read_time = time.time() - start_time

compression_ratio = read_write_zarr.get_compression_ratio(store_path)
storage_size = utils.get_directory_size(store_path) / (1024**2)

results['gzip'] = {
    'write_time': write_time,
    'read_time': read_time,
    'compression_ratio': compression_ratio,
    'storage_size_mb': storage_size
}

print(f"   ✓ Write time: {write_time:.3f}s")
print(f"   ✓ Read time: {read_time:.3f}s")
print(f"   ✓ Compression ratio: {compression_ratio:.2f}x")
print(f"   ✓ Storage size: {storage_size:.2f} MB")
print(f"   ✓ Data integrity: {np.allclose(sample_image, read_image)}")

# ============================================================================
# 5. TEST ZSTD COMPRESSION
# ============================================================================
print("\n🔧 5. Testing Zstd Compression...")
store_path = output_dir / "zstd_compressed.zarr"
zstd_compressor = read_write_zarr.get_zstd_compressor(
    level=5,
    zarr_spec=zarr_spec
)

utils.remove_output_dir(store_path)
start_time = time.time()
read_write_zarr.write_zarr_array(
    sample_image,
    store_path,
    overwrite=False,
    chunks=chunks,
    compressor=zstd_compressor,
    zarr_spec=zarr_spec
)
write_time = time.time() - start_time

start_time = time.time()
read_image = read_write_zarr.read_zarr_array(store_path)
read_time = time.time() - start_time

compression_ratio = read_write_zarr.get_compression_ratio(store_path)
storage_size = utils.get_directory_size(store_path) / (1024**2)

results['zstd'] = {
    'write_time': write_time,
    'read_time': read_time,
    'compression_ratio': compression_ratio,
    'storage_size_mb': storage_size
}

print(f"   ✓ Write time: {write_time:.3f}s")
print(f"   ✓ Read time: {read_time:.3f}s")
print(f"   ✓ Compression ratio: {compression_ratio:.2f}x")
print(f"   ✓ Storage size: {storage_size:.2f} MB")
print(f"   ✓ Data integrity: {np.allclose(sample_image, read_image)}")

# ============================================================================
# 6. TEST NO COMPRESSION (BASELINE)
# ============================================================================
print("\n🔧 6. Testing No Compression (Baseline)...")
store_path = output_dir / "no_compression.zarr"

utils.remove_output_dir(store_path)
start_time = time.time()
read_write_zarr.write_zarr_array(
    sample_image,
    store_path,
    overwrite=False,
    chunks=chunks,
    compressor=None,
    zarr_spec=zarr_spec
)
write_time = time.time() - start_time

start_time = time.time()
read_image = read_write_zarr.read_zarr_array(store_path)
read_time = time.time() - start_time

compression_ratio = read_write_zarr.get_compression_ratio(store_path)
storage_size = utils.get_directory_size(store_path) / (1024**2)

results['no_compression'] = {
    'write_time': write_time,
    'read_time': read_time,
    'compression_ratio': compression_ratio,
    'storage_size_mb': storage_size
}

print(f"   ✓ Write time: {write_time:.3f}s")
print(f"   ✓ Read time: {read_time:.3f}s")
print(f"   ✓ Compression ratio: {compression_ratio:.2f}x")
print(f"   ✓ Storage size: {storage_size:.2f} MB")
print(f"   ✓ Data integrity: {np.allclose(sample_image, read_image)}")

# ============================================================================
# 7. SUMMARY TABLE
# ============================================================================
print("\n" + "=" * 70)
print("📈 BENCHMARK SUMMARY")
print("=" * 70)

summary_df = pd.DataFrame(results).T
summary_df = summary_df.round(3)
summary_df.columns = ['Write Time (s)', 'Read Time (s)', 'Compression Ratio', 'Storage Size (MB)']

print("\n" + summary_df.to_string())

print("\n🏆 Best Methods:")
print(f"   Fastest write: {summary_df['Write Time (s)'].idxmin()}")
print(f"   Fastest read: {summary_df['Read Time (s)'].idxmin()}")
print(f"   Best compression: {summary_df['Compression Ratio'].idxmax()}")
print(f"   Smallest storage: {summary_df['Storage Size (MB)'].idxmin()}")

# ============================================================================
# 8. CREATE COMPARISON PLOTS
# ============================================================================
print("\n📊 Generating comparison plots...")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

methods = list(results.keys())
write_times = [results[m]['write_time'] for m in methods]
read_times = [results[m]['read_time'] for m in methods]
compression_ratios = [results[m]['compression_ratio'] for m in methods]
storage_sizes = [results[m]['storage_size_mb'] for m in methods]

# Plot 1: Write times
axes[0, 0].bar(methods, write_times, color='steelblue')
axes[0, 0].set_ylabel('Time (seconds)')
axes[0, 0].set_title('Write Performance')
axes[0, 0].tick_params(axis='x', rotation=45)

# Plot 2: Read times
axes[0, 1].bar(methods, read_times, color='coral')
axes[0, 1].set_ylabel('Time (seconds)')
axes[0, 1].set_title('Read Performance')
axes[0, 1].tick_params(axis='x', rotation=45)

# Plot 3: Compression ratios
axes[1, 0].bar(methods, compression_ratios, color='green')
axes[1, 0].set_ylabel('Compression Ratio')
axes[1, 0].set_title('Compression Ratio (Higher is Better)')
axes[1, 0].tick_params(axis='x', rotation=45)

# Plot 4: Storage sizes
axes[1, 1].bar(methods, storage_sizes, color='purple')
axes[1, 1].set_ylabel('Size (MB)')
axes[1, 1].set_title('Storage Size (Lower is Better)')
axes[1, 1].tick_params(axis='x', rotation=45)

plt.tight_layout()

# Save the plot
plot_path = output_dir / "benchmark_comparison.png"
plt.savefig(plot_path, dpi=150, bbox_inches='tight')
print(f"   ✓ Plot saved to: {plot_path}")

# Show the plot
plt.show()

print("\n" + "=" * 70)
print("✅ BENCHMARKS COMPLETED SUCCESSFULLY!")
print("=" * 70)
print(f"\nResults saved to: {output_dir}")
print(f"Plot saved to: {plot_path}")
