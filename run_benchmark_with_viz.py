#!/usr/bin/env python3
"""
Zarr Benchmarks Demo with Data Visualization
This script visualizes the sample data BEFORE running benchmarks.
"""

import numpy as np
import pathlib
import time
import pandas as pd
import matplotlib.pyplot as plt
from zarr_benchmarks.read_write_zarr import read_write_zarr
from zarr_benchmarks import utils

print("=" * 70)
print("ZARR BENCHMARKS DEMO WITH DATA VISUALIZATION")
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
print(f"   Data range: [{sample_image.min():.3f}, {sample_image.max():.3f}]")
print(f"   Data mean: {sample_image.mean():.3f}")
print(f"   Data std: {sample_image.std():.3f}")

# ============================================================================
# 2. VISUALIZE THE DATA
# ============================================================================
print("\n📸 2. Visualizing the 3D data (slicing through different planes)...")

fig = plt.figure(figsize=(16, 12))

# Create a 3x3 grid of subplots
# Row 1: XY plane at different Z positions
# Row 2: XZ plane at different Y positions
# Row 3: YZ plane at different X positions

# XY slices (looking down through Z)
for i, z_pos in enumerate([image_size//4, image_size//2, 3*image_size//4]):
    ax = plt.subplot(3, 3, i+1)
    im = ax.imshow(sample_image[z_pos, :, :], cmap='viridis', aspect='auto')
    ax.set_title(f'XY Slice (Z={z_pos})')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    plt.colorbar(im, ax=ax, fraction=0.046)

# XZ slices (looking from the side, Y direction)
for i, y_pos in enumerate([image_size//4, image_size//2, 3*image_size//4]):
    ax = plt.subplot(3, 3, i+4)
    im = ax.imshow(sample_image[:, y_pos, :], cmap='plasma', aspect='auto')
    ax.set_title(f'XZ Slice (Y={y_pos})')
    ax.set_xlabel('X')
    ax.set_ylabel('Z')
    plt.colorbar(im, ax=ax, fraction=0.046)

# YZ slices (looking from the side, X direction)
for i, x_pos in enumerate([image_size//4, image_size//2, 3*image_size//4]):
    ax = plt.subplot(3, 3, i+7)
    im = ax.imshow(sample_image[:, :, x_pos], cmap='inferno', aspect='auto')
    ax.set_title(f'YZ Slice (X={x_pos})')
    ax.set_xlabel('Y')
    ax.set_ylabel('Z')
    plt.colorbar(im, ax=ax, fraction=0.046)

plt.tight_layout()

# Save the visualization
viz_dir = pathlib.Path("data/output/visualizations")
viz_dir.mkdir(parents=True, exist_ok=True)
viz_path = viz_dir / "sample_data_slices.png"
plt.savefig(viz_path, dpi=150, bbox_inches='tight')
print(f"   ✓ Data visualization saved to: {viz_path}")
plt.show()

# ============================================================================
# 3. HISTOGRAM OF DATA VALUES
# ============================================================================
print("\n📊 3. Analyzing data distribution...")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Histogram
axes[0].hist(sample_image.flatten(), bins=50, color='steelblue', alpha=0.7, edgecolor='black')
axes[0].set_xlabel('Pixel Value')
axes[0].set_ylabel('Frequency')
axes[0].set_title('Distribution of Pixel Values')
axes[0].grid(True, alpha=0.3)

# Statistics box plot
sample_slices = [
    sample_image[image_size//4, :, :].flatten(),
    sample_image[image_size//2, :, :].flatten(),
    sample_image[3*image_size//4, :, :].flatten()
]
axes[1].boxplot(sample_slices, labels=['Z=64', 'Z=128', 'Z=192'])
axes[1].set_ylabel('Pixel Value')
axes[1].set_title('Distribution Across Different Z Slices')
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
hist_path = viz_dir / "data_distribution.png"
plt.savefig(hist_path, dpi=150, bbox_inches='tight')
print(f"   ✓ Distribution analysis saved to: {hist_path}")
plt.show()

# ============================================================================
# 4. INTERACTIVE DATA EXPLORATION
# ============================================================================
print("\n🔍 4. Data statistics by region...")

# Analyze different regions
regions = {
    'Top Quarter': sample_image[:image_size//4, :, :],
    'Middle Half': sample_image[image_size//4:3*image_size//4, :, :],
    'Bottom Quarter': sample_image[3*image_size//4:, :, :],
}

stats_data = []
for region_name, region_data in regions.items():
    stats_data.append({
        'Region': region_name,
        'Mean': region_data.mean(),
        'Std': region_data.std(),
        'Min': region_data.min(),
        'Max': region_data.max(),
        'Size (MB)': region_data.nbytes / (1024**2)
    })

stats_df = pd.DataFrame(stats_data)
print("\n" + stats_df.to_string(index=False))

# Wait for user input before continuing
print("\n" + "=" * 70)
input("Press ENTER to continue with benchmarking...")
print("=" * 70)

# ============================================================================
# 5. SETUP BENCHMARK PARAMETERS
# ============================================================================
print("\n⚙️  5. Setting up benchmark parameters...")
output_dir = pathlib.Path("data/output/demo_benchmarks")
output_dir.mkdir(parents=True, exist_ok=True)

chunk_size = 64
chunks = (chunk_size, chunk_size, chunk_size)
zarr_spec = 3

results = {}
print(f"   Chunk size: {chunk_size}x{chunk_size}x{chunk_size}")
print(f"   Zarr spec: v{zarr_spec}")

# ============================================================================
# 6. RUN BENCHMARKS
# ============================================================================
compression_methods = [
    ('blosc', 'Blosc-Zstd', lambda: read_write_zarr.get_blosc_compressor("zstd", 5, "shuffle", zarr_spec)),
    ('gzip', 'GZip', lambda: read_write_zarr.get_gzip_compressor(6, zarr_spec)),
    ('zstd', 'Zstd', lambda: read_write_zarr.get_zstd_compressor(5, zarr_spec)),
    ('no_compression', 'No Compression', lambda: None),
]

for idx, (method_key, method_name, get_compressor) in enumerate(compression_methods, start=6):
    print(f"\n🔧 {idx}. Testing {method_name}...")
    store_path = output_dir / f"{method_key}.zarr"
    compressor = get_compressor()

    utils.remove_output_dir(store_path)
    start_time = time.time()
    read_write_zarr.write_zarr_array(
        sample_image,
        store_path,
        overwrite=False,
        chunks=chunks,
        compressor=compressor,
        zarr_spec=zarr_spec
    )
    write_time = time.time() - start_time

    start_time = time.time()
    read_image = read_write_zarr.read_zarr_array(store_path)
    read_time = time.time() - start_time

    compression_ratio = read_write_zarr.get_compression_ratio(store_path)
    storage_size = utils.get_directory_size(store_path) / (1024**2)

    results[method_key] = {
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
print(f"Visualizations saved to: {viz_dir}")
print(f"Benchmark plot: {plot_path}")
