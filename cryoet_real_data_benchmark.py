#!/usr/bin/env python3
"""
CryoET Real Data Benchmark with Visualization
Download, visualize, and benchmark real cryo-EM tomography data from the CryoET portal
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
print("CRYOET REAL DATA BENCHMARK WITH VISUALIZATION")
print("=" * 70)

# ============================================================================
# 1. CONNECT TO CRYOET PORTAL
# ============================================================================
print("\n📡 1. Connecting to CryoET Data Portal...")
client = Client()
dataset = Dataset.get_by_id(client, 10445)

print(f"   ✓ Dataset: {dataset.title}")
print(f"   ✓ Dataset ID: {dataset.id}")

# ============================================================================
# 2. GET TOMOGRAM INFORMATION
# ============================================================================
print("\n🔍 2. Fetching tomogram metadata...")
runs = list(dataset.runs)
first_run = runs[0]
tomograms = list(first_run.tomograms)
first_tomo = tomograms[0]

print(f"   ✓ Run: {first_run.name}")
print(f"   ✓ Tomogram: {first_tomo.name}")
print(f"   ✓ Size: {first_tomo.size_x} x {first_tomo.size_y} x {first_tomo.size_z}")
print(f"   ✓ Voxel spacing: {first_tomo.voxel_spacing} Å")
print(f"   ✓ Total tomograms in dataset: {len(tomograms)} (in this run)")

# ============================================================================
# 3. ACCESS ZARR DATA FROM S3
# ============================================================================
print("\n☁️  3. Accessing Zarr data from S3...")
s3 = s3fs.S3FileSystem(anon=True)
zarr_path = first_tomo.s3_omezarr_dir.replace("s3://", "")

store = s3fs.S3Map(root=zarr_path, s3=s3, check=False)
zarr_group = zarr.open(store, mode="r")
zarr_array = zarr_group["0"]  # Full resolution data

print(f"   ✓ Shape: {zarr_array.shape} (Z, Y, X)")
print(f"   ✓ Dtype: {zarr_array.dtype}")
print(f"   ✓ Chunks: {zarr_array.chunks}")
print(f"   ✓ Original compressor: Blosc(lz4)")
print(f"   ✓ Size: {zarr_array.nbytes / (1024**3):.2f} GB (uncompressed)")

# ============================================================================
# 4. DOWNLOAD A SUBSET FOR BENCHMARKING
# ============================================================================
print("\n⬇️  4. Downloading a subset of the data for benchmarking...")
print("   (Downloading a 256x256x256 cube from the center)")

# Calculate center position
z_center = zarr_array.shape[0] // 2
y_center = zarr_array.shape[1] // 2
x_center = zarr_array.shape[2] // 2

# Define subset size
subset_size = 128  # Smaller for faster download

# Calculate slice ranges (centered)
z_start = max(0, z_center - subset_size // 2)
z_end = min(zarr_array.shape[0], z_start + subset_size)
y_start = max(0, y_center - subset_size // 2)
y_end = min(zarr_array.shape[1], y_start + subset_size)
x_start = max(0, x_center - subset_size // 2)
x_end = min(zarr_array.shape[2], x_start + subset_size)

print(f"   Downloading Z:{z_start}-{z_end}, Y:{y_start}-{y_end}, X:{x_start}-{x_end}")

start_time = time.time()
real_data = np.array(zarr_array[z_start:z_end, y_start:y_end, x_start:x_end])
download_time = time.time() - start_time

actual_shape = real_data.shape
print(f"   ✓ Downloaded in {download_time:.2f}s")
print(f"   ✓ Actual shape: {actual_shape}")
print(f"   ✓ Downloaded size: {real_data.nbytes / (1024**2):.2f} MB")
print(f"   ✓ Data range: [{real_data.min():.3f}, {real_data.max():.3f}]")
print(f"   ✓ Data mean: {real_data.mean():.3f}")
print(f"   ✓ Data std: {real_data.std():.3f}")

# ============================================================================
# 5. VISUALIZE THE CRYO-EM DATA
# ============================================================================
print("\n📸 5. Visualizing the cryo-EM tomogram data...")

fig = plt.figure(figsize=(16, 12))
fig.suptitle(
    f"CryoET Data: {first_tomo.name} (Dataset {dataset.id})", fontsize=16, fontweight="bold"
)

# XY slices at different Z positions
for i, z_pos in enumerate([actual_shape[0] // 4, actual_shape[0] // 2, 3 * actual_shape[0] // 4]):
    ax = plt.subplot(3, 3, i + 1)
    im = ax.imshow(real_data[z_pos, :, :], cmap="gray", vmin=real_data.min(), vmax=real_data.max())
    ax.set_title(f"XY Slice (Z={z_pos})")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    plt.colorbar(im, ax=ax, fraction=0.046)

# XZ slices at different Y positions
for i, y_pos in enumerate([actual_shape[1] // 4, actual_shape[1] // 2, 3 * actual_shape[1] // 4]):
    ax = plt.subplot(3, 3, i + 4)
    im = ax.imshow(real_data[:, y_pos, :], cmap="gray", vmin=real_data.min(), vmax=real_data.max())
    ax.set_title(f"XZ Slice (Y={y_pos})")
    ax.set_xlabel("X")
    ax.set_ylabel("Z")
    plt.colorbar(im, ax=ax, fraction=0.046)

# YZ slices at different X positions
for i, x_pos in enumerate([actual_shape[2] // 4, actual_shape[2] // 2, 3 * actual_shape[2] // 4]):
    ax = plt.subplot(3, 3, i + 7)
    im = ax.imshow(real_data[:, :, x_pos], cmap="gray", vmin=real_data.min(), vmax=real_data.max())
    ax.set_title(f"YZ Slice (X={x_pos})")
    ax.set_xlabel("Y")
    ax.set_ylabel("Z")
    plt.colorbar(im, ax=ax, fraction=0.046)

plt.tight_layout()

viz_dir = pathlib.Path("data/output/cryoet_viz")
viz_dir.mkdir(parents=True, exist_ok=True)
viz_path = viz_dir / "cryoet_data_slices.png"
plt.savefig(viz_path, dpi=150, bbox_inches="tight")
print(f"   ✓ Visualization saved to: {viz_path}")
plt.show()

# ============================================================================
# 6. DATA DISTRIBUTION ANALYSIS
# ============================================================================
print("\n📊 6. Analyzing data distribution...")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Histogram
axes[0].hist(real_data.flatten(), bins=100, color="steelblue", alpha=0.7, edgecolor="black")
axes[0].set_xlabel("Voxel Intensity")
axes[0].set_ylabel("Frequency")
axes[0].set_title(f"CryoET Data Distribution\n{first_tomo.name}")
axes[0].grid(True, alpha=0.3)

# Box plot by slice
sample_slices = [
    real_data[actual_shape[0] // 4, :, :].flatten(),
    real_data[actual_shape[0] // 2, :, :].flatten(),
    real_data[3 * actual_shape[0] // 4, :, :].flatten(),
]
axes[1].boxplot(sample_slices, tick_labels=["Z=Q1", "Z=Q2", "Z=Q3"])
axes[1].set_ylabel("Voxel Intensity")
axes[1].set_title("Distribution Across Z Slices")
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
dist_path = viz_dir / "cryoet_distribution.png"
plt.savefig(dist_path, dpi=150, bbox_inches="tight")
print(f"   ✓ Distribution analysis saved to: {dist_path}")
plt.show()

# Wait for user
print("\n" + "=" * 70)
input("Press ENTER to continue with benchmarking...")
print("=" * 70)

# ============================================================================
# 7. BENCHMARK DIFFERENT COMPRESSION METHODS
# ============================================================================
print("\n⚙️  7. Benchmarking different compression methods on real CryoET data...")

output_dir = pathlib.Path("data/output/cryoet_benchmarks")
output_dir.mkdir(parents=True, exist_ok=True)

# Use smaller chunks for this data
chunk_size = 64
chunks = (chunk_size, chunk_size, chunk_size)
zarr_spec = 3

results = {}
compression_methods = [
    (
        "blosc_zstd",
        "Blosc-Zstd",
        lambda: read_write_zarr.get_blosc_compressor("zstd", 5, "shuffle", zarr_spec),
    ),
    (
        "blosc_lz4",
        "Blosc-LZ4 (Original)",
        lambda: read_write_zarr.get_blosc_compressor("lz4", 5, "shuffle", zarr_spec),
    ),
    ("gzip", "GZip", lambda: read_write_zarr.get_gzip_compressor(6, zarr_spec)),
    ("zstd", "Zstd", lambda: read_write_zarr.get_zstd_compressor(5, zarr_spec)),
    ("no_compression", "No Compression", lambda: None),
]

for method_key, method_name, get_compressor in compression_methods:
    print(f"\n🔧 Testing {method_name}...")
    store_path = output_dir / f"{method_key}.zarr"
    compressor = get_compressor()

    utils.remove_output_dir(store_path)
    start_time = time.time()
    read_write_zarr.write_zarr_array(
        real_data,
        store_path,
        overwrite=False,
        chunks=chunks,
        compressor=compressor,
        zarr_spec=zarr_spec,
    )
    write_time = time.time() - start_time

    start_time = time.time()
    read_back = read_write_zarr.read_zarr_array(store_path)
    read_time = time.time() - start_time

    compression_ratio = read_write_zarr.get_compression_ratio(store_path)
    storage_size = utils.get_directory_size(store_path) / (1024**2)

    results[method_key] = {
        "write_time": write_time,
        "read_time": read_time,
        "compression_ratio": compression_ratio,
        "storage_size_mb": storage_size,
    }

    print(f"   ✓ Write time: {write_time:.3f}s")
    print(f"   ✓ Read time: {read_time:.3f}s")
    print(f"   ✓ Compression ratio: {compression_ratio:.2f}x")
    print(f"   ✓ Storage size: {storage_size:.2f} MB")
    print(f"   ✓ Data integrity: {np.allclose(real_data, read_back)}")

# ============================================================================
# 8. BENCHMARK SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("📈 CRYOET DATA BENCHMARK SUMMARY")
print("=" * 70)

summary_df = pd.DataFrame(results).T
summary_df = summary_df.round(3)
summary_df.columns = ["Write Time (s)", "Read Time (s)", "Compression Ratio", "Storage Size (MB)"]

print("\n" + summary_df.to_string())

print("\n🏆 Best Methods for CryoET Data:")
print(f"   Fastest write: {summary_df['Write Time (s)'].idxmin()}")
print(f"   Fastest read: {summary_df['Read Time (s)'].idxmin()}")
print(f"   Best compression: {summary_df['Compression Ratio'].idxmax()}")
print(f"   Smallest storage: {summary_df['Storage Size (MB)'].idxmin()}")

# ============================================================================
# 9. COMPARISON PLOTS
# ============================================================================
print("\n📊 Generating comparison plots...")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle(
    f"Compression Benchmark Results: CryoET Data ({first_tomo.name})",
    fontsize=14,
    fontweight="bold",
)

methods = list(results.keys())
write_times = [results[m]["write_time"] for m in methods]
read_times = [results[m]["read_time"] for m in methods]
compression_ratios = [results[m]["compression_ratio"] for m in methods]
storage_sizes = [results[m]["storage_size_mb"] for m in methods]

axes[0, 0].bar(methods, write_times, color="steelblue")
axes[0, 0].set_ylabel("Time (seconds)")
axes[0, 0].set_title("Write Performance")
axes[0, 0].tick_params(axis="x", rotation=45)

axes[0, 1].bar(methods, read_times, color="coral")
axes[0, 1].set_ylabel("Time (seconds)")
axes[0, 1].set_title("Read Performance")
axes[0, 1].tick_params(axis="x", rotation=45)

axes[1, 0].bar(methods, compression_ratios, color="green")
axes[1, 0].set_ylabel("Compression Ratio")
axes[1, 0].set_title("Compression Ratio (Higher is Better)")
axes[1, 0].tick_params(axis="x", rotation=45)

axes[1, 1].bar(methods, storage_sizes, color="purple")
axes[1, 1].set_ylabel("Size (MB)")
axes[1, 1].set_title("Storage Size (Lower is Better)")
axes[1, 1].tick_params(axis="x", rotation=45)

plt.tight_layout()
plot_path = output_dir / "cryoet_benchmark_comparison.png"
plt.savefig(plot_path, dpi=150, bbox_inches="tight")
print(f"   ✓ Plot saved to: {plot_path}")
plt.show()

# ============================================================================
# 10. FINAL SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("✅ CRYOET DATA BENCHMARK COMPLETED!")
print("=" * 70)

print(f"\nDataset Information:")
print(f"  - Dataset: {dataset.title}")
print(f"  - Tomogram: {first_tomo.name}")
print(f"  - Full size: {first_tomo.size_x} x {first_tomo.size_y} x {first_tomo.size_z}")
print(f"  - Benchmarked subset: {actual_shape}")
print(f"  - Voxel spacing: {first_tomo.voxel_spacing} Å")
print(f"  - Original compression: Blosc(lz4)")

print(f"\nFiles saved:")
print(f"  - Visualizations: {viz_dir}/")
print(f"  - Benchmark data: {output_dir}/")
print(f"  - Comparison plot: {plot_path}")

print(f"\n💡 Key Findings:")
original_size = real_data.nbytes / (1024**2)
best_method = summary_df["Compression Ratio"].idxmax()
best_ratio = summary_df.loc[best_method, "Compression Ratio"]
best_size = summary_df.loc[best_method, "Storage Size (MB)"]
savings = original_size - best_size

print(f"  - Original size: {original_size:.2f} MB")
print(f"  - Best compression: {best_method} ({best_ratio:.2f}x)")
print(f"  - Compressed size: {best_size:.2f} MB")
print(f"  - Space saved: {savings:.2f} MB ({(savings/original_size)*100:.1f}%)")
