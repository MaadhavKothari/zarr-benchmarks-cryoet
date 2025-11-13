#!/usr/bin/env python3
"""
CryoET Real Data Quick Benchmark (No Pause)
Download, visualize, and benchmark real cryo-EM tomography data
"""

import numpy as np
import pathlib
import time
import pandas as pd
import matplotlib.pyplot as plt
from cryoet_data_portal import Client, Dataset
import s3fs
import zarr
from zarr_benchmarks.read_write_zarr import read_write_zarr
from zarr_benchmarks import utils

print("=" * 70)
print("CRYOET REAL DATA QUICK BENCHMARK")
print("=" * 70)

# Connect to portal
print("\n📡 1. Connecting to CryoET Portal...")
client = Client()
dataset = Dataset.get_by_id(client, 10445)
print(f"   ✓ Dataset: {dataset.title}")

# Get tomogram
print("\n🔍 2. Fetching tomogram...")
runs = list(dataset.runs)
first_run = runs[0]
tomograms = list(first_run.tomograms)
first_tomo = tomograms[0]
print(f"   ✓ Tomogram: {first_tomo.name}")
print(f"   ✓ Size: {first_tomo.size_x} x {first_tomo.size_y} x {first_tomo.size_z}")
print(f"   ✓ Voxel spacing: {first_tomo.voxel_spacing} Å")

# Access S3 data
print("\n☁️  3. Accessing data from S3...")
s3 = s3fs.S3FileSystem(anon=True)
zarr_path = first_tomo.s3_omezarr_dir.replace('s3://', '')
store = s3fs.S3Map(root=zarr_path, s3=s3, check=False)
zarr_group = zarr.open(store, mode='r')
zarr_array = zarr_group['0']
print(f"   ✓ Shape: {zarr_array.shape} (Z, Y, X)")
print(f"   ✓ Size: {zarr_array.nbytes / (1024**3):.2f} GB")

# Download subset
print("\n⬇️  4. Downloading 128³ subset from center...")
z_c, y_c, x_c = zarr_array.shape[0]//2, zarr_array.shape[1]//2, zarr_array.shape[2]//2
size = 128

start_time = time.time()
real_data = np.array(zarr_array[
    max(0, z_c-size//2):min(zarr_array.shape[0], z_c+size//2),
    max(0, y_c-size//2):min(zarr_array.shape[1], y_c+size//2),
    max(0, x_c-size//2):min(zarr_array.shape[2], x_c+size//2)
])
download_time = time.time() - start_time

print(f"   ✓ Downloaded {real_data.shape} in {download_time:.2f}s")
print(f"   ✓ Size: {real_data.nbytes / (1024**2):.2f} MB")
print(f"   ✓ Range: [{real_data.min():.2f}, {real_data.max():.2f}]")

# Visualize
print("\n📸 5. Creating visualizations...")
viz_dir = pathlib.Path("data/output/cryoet_viz")
viz_dir.mkdir(parents=True, exist_ok=True)

# Main slices
fig, axes = plt.subplots(2, 3, figsize=(15, 10))
fig.suptitle(f'CryoET Data: {first_tomo.name}', fontsize=14, fontweight='bold')

# Middle slices
mid_z, mid_y, mid_x = real_data.shape[0]//2, real_data.shape[1]//2, real_data.shape[2]//2

axes[0, 0].imshow(real_data[mid_z, :, :], cmap='gray')
axes[0, 0].set_title('XY Slice (middle Z)')
axes[0, 1].imshow(real_data[:, mid_y, :], cmap='gray')
axes[0, 1].set_title('XZ Slice (middle Y)')
axes[0, 2].imshow(real_data[:, :, mid_x], cmap='gray')
axes[0, 2].set_title('YZ Slice (middle X)')

# Histogram and stats
axes[1, 0].hist(real_data.flatten(), bins=100, color='steelblue', alpha=0.7)
axes[1, 0].set_title('Intensity Distribution')
axes[1, 0].set_xlabel('Intensity')
axes[1, 0].set_ylabel('Frequency')

# Stats text
stats_text = f"""
Shape: {real_data.shape}
Min: {real_data.min():.2f}
Max: {real_data.max():.2f}
Mean: {real_data.mean():.2f}
Std: {real_data.std():.2f}
"""
axes[1, 1].text(0.1, 0.5, stats_text, fontsize=12, family='monospace')
axes[1, 1].axis('off')
axes[1, 1].set_title('Data Statistics')

# Empty for now
axes[1, 2].axis('off')

plt.tight_layout()
viz_path = viz_dir / "cryoet_quick_viz.png"
plt.savefig(viz_path, dpi=150, bbox_inches='tight')
print(f"   ✓ Saved to: {viz_path}")
plt.close()

# Benchmark
print("\n⚙️  6. Running compression benchmarks...")
output_dir = pathlib.Path("data/output/cryoet_benchmarks")
output_dir.mkdir(parents=True, exist_ok=True)

chunk_size = 64
chunks = (chunk_size, chunk_size, chunk_size)
zarr_spec = 3
results = {}

methods = [
    ('blosc_lz4', 'Blosc-LZ4', lambda: read_write_zarr.get_blosc_compressor("lz4", 5, "shuffle", zarr_spec)),
    ('blosc_zstd', 'Blosc-Zstd', lambda: read_write_zarr.get_blosc_compressor("zstd", 5, "shuffle", zarr_spec)),
    ('zstd', 'Zstd', lambda: read_write_zarr.get_zstd_compressor(5, zarr_spec)),
    ('no_compression', 'None', lambda: None),
]

for key, name, get_comp in methods:
    print(f"   Testing {name}...")
    store_path = output_dir / f"{key}.zarr"

    utils.remove_output_dir(store_path)

    t0 = time.time()
    read_write_zarr.write_zarr_array(real_data, store_path, overwrite=False,
                                      chunks=chunks, compressor=get_comp(), zarr_spec=zarr_spec)
    write_time = time.time() - t0

    t0 = time.time()
    read_back = read_write_zarr.read_zarr_array(store_path)
    read_time = time.time() - t0

    ratio = read_write_zarr.get_compression_ratio(store_path)
    size_mb = utils.get_directory_size(store_path) / (1024**2)

    results[key] = {
        'write_time': write_time,
        'read_time': read_time,
        'compression_ratio': ratio,
        'storage_size_mb': size_mb
    }

    print(f"     Write: {write_time:.3f}s, Read: {read_time:.3f}s, Ratio: {ratio:.2f}x, Size: {size_mb:.2f}MB")

# Summary
print("\n" + "=" * 70)
print("📈 BENCHMARK RESULTS")
print("=" * 70)

df = pd.DataFrame(results).T
df = df.round(3)
df.columns = ['Write (s)', 'Read (s)', 'Ratio', 'Size (MB)']
print("\n" + df.to_string())

print("\n🏆 Best for CryoET Data:")
print(f"   Fastest write: {df['Write (s)'].idxmin()}")
print(f"   Fastest read: {df['Read (s)'].idxmin()}")
print(f"   Best compression: {df['Ratio'].idxmax()} ({df['Ratio'].max():.2f}x)")

# Plot
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
fig.suptitle('CryoET Data Compression Benchmark', fontsize=14, fontweight='bold')

methods = list(results.keys())
axes[0, 0].bar(methods, [results[m]['write_time'] for m in methods], color='steelblue')
axes[0, 0].set_title('Write Performance')
axes[0, 0].set_ylabel('Time (s)')
axes[0, 0].tick_params(axis='x', rotation=45)

axes[0, 1].bar(methods, [results[m]['read_time'] for m in methods], color='coral')
axes[0, 1].set_title('Read Performance')
axes[0, 1].set_ylabel('Time (s)')
axes[0, 1].tick_params(axis='x', rotation=45)

axes[1, 0].bar(methods, [results[m]['compression_ratio'] for m in methods], color='green')
axes[1, 0].set_title('Compression Ratio')
axes[1, 0].set_ylabel('Ratio')
axes[1, 0].tick_params(axis='x', rotation=45)

axes[1, 1].bar(methods, [results[m]['storage_size_mb'] for m in methods], color='purple')
axes[1, 1].set_title('Storage Size')
axes[1, 1].set_ylabel('Size (MB)')
axes[1, 1].tick_params(axis='x', rotation=45)

plt.tight_layout()
plot_path = output_dir / "cryoet_benchmark.png"
plt.savefig(plot_path, dpi=150, bbox_inches='tight')
print(f"\n✓ Benchmark plot saved to: {plot_path}")
plt.close()

print("\n" + "=" * 70)
print("✅ COMPLETE!")
print("=" * 70)
print(f"\nVisualization: {viz_path}")
print(f"Benchmark plot: {plot_path}")
print(f"Benchmark data: {output_dir}/")
