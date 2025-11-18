#!/usr/bin/env python3
"""
CryoET Zarr Chunking Benchmark (Zarr v2 Compatible)
Test different chunk sizes and their impact on performance and file count
"""

import pathlib
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import s3fs
import zarr
from cryoet_data_portal import Client, Dataset
from numcodecs import Blosc

from zarr_benchmarks import utils

print("=" * 80)
print("CRYOET ZARR CHUNKING BENCHMARK")
print("=" * 80)

# ============================================================================
# 1. DOWNLOAD CRYOET DATA
# ============================================================================
print("\n📡 1. Connecting to CryoET Portal and downloading data...")
client = Client()
dataset = Dataset.get_by_id(client, 10445)

runs = list(dataset.runs)
first_run = runs[0]
tomograms = list(first_run.tomograms)
first_tomo = tomograms[0]

print(f"   ✓ Dataset: {dataset.title}")
print(f"   ✓ Tomogram: {first_tomo.name}")

# Access S3 data
s3 = s3fs.S3FileSystem(anon=True)
zarr_path = first_tomo.s3_omezarr_dir.replace("s3://", "")
store = s3fs.S3Map(root=zarr_path, s3=s3, check=False)
zarr_group = zarr.open(store, mode="r")
zarr_array = zarr_group["0"]

# Download 128³ subset from center
z_c, y_c, x_c = (
    zarr_array.shape[0] // 2,
    zarr_array.shape[1] // 2,
    zarr_array.shape[2] // 2,
)
size = 128

start_time = time.time()
real_data = np.array(
    zarr_array[
        max(0, z_c - size // 2) : min(zarr_array.shape[0], z_c + size // 2),
        max(0, y_c - size // 2) : min(zarr_array.shape[1], y_c + size // 2),
        max(0, x_c - size // 2) : min(zarr_array.shape[2], x_c + size // 2),
    ]
)
download_time = time.time() - start_time

print(f"   ✓ Downloaded {real_data.shape} in {download_time:.2f}s")
print(f"   ✓ Size: {real_data.nbytes / (1024**2):.2f} MB")

# ============================================================================
# 2. HELPER FUNCTIONS
# ============================================================================


def count_files_in_zarr(store_path: pathlib.Path) -> int:
    """Count total files in zarr store (including metadata)"""
    count = 0
    if store_path.exists():
        for item in store_path.rglob("*"):
            if item.is_file():
                count += 1
    return count


def count_data_chunks(store_path: pathlib.Path) -> int:
    """Count actual data chunk files (not metadata)"""
    count = 0
    if store_path.exists():
        # In zarr v2, chunks are typically in numbered files
        for item in store_path.rglob("*"):
            if item.is_file() and item.name.isdigit():
                count += 1
    return count


def benchmark_chunk_config(name, data, store_path, chunks, compressor):
    """Benchmark a single chunk configuration"""
    utils.remove_output_dir(store_path)

    # Write
    t0 = time.time()
    zarr_arr = zarr.open_array(
        store_path,
        mode="w",
        shape=data.shape,
        chunks=chunks,
        dtype=data.dtype,
        compressor=compressor,
    )
    zarr_arr[:] = data
    write_time = time.time() - t0

    # Read - full array
    t0 = time.time()
    zarr_read = zarr.open_array(store_path, mode="r")
    read_back = zarr_read[:]
    read_time_full = time.time() - t0

    # Read - single chunk (to measure chunk read time)
    chunk_size = chunks[0]
    t0 = time.time()
    _ = zarr_read[0:chunk_size, 0:chunk_size, 0:chunk_size]  # Read for timing only
    read_time_chunk = time.time() - t0

    # Read - single slice (common operation)
    t0 = time.time()
    _ = zarr_read[data.shape[0] // 2, :, :]  # Read for timing only
    read_time_slice = time.time() - t0

    # Verify data integrity
    assert np.allclose(data, read_back), f"Data mismatch for {name}!"

    # Metrics
    storage_size = utils.get_directory_size(store_path) / (1024**2)
    file_count = count_files_in_zarr(store_path)
    chunk_count = count_data_chunks(store_path)
    compression_ratio = data.nbytes / (storage_size * 1024**2)

    # Calculate theoretical chunk count
    theoretical_chunks = np.prod(
        [int(np.ceil(s / c)) for s, c in zip(data.shape, chunks)]
    )

    return {
        "name": name,
        "chunk_size": chunk_size,
        "chunks_shape": f"{chunks[0]}³",
        "write_time": write_time,
        "read_time_full": read_time_full,
        "read_time_chunk": read_time_chunk,
        "read_time_slice": read_time_slice,
        "storage_mb": storage_size,
        "compression_ratio": compression_ratio,
        "file_count": file_count,
        "chunk_count": chunk_count,
        "theoretical_chunks": theoretical_chunks,
    }


# ============================================================================
# 3. BENCHMARK CONFIGURATIONS
# ============================================================================
print("\n⚙️  2. Running chunking benchmarks...")
print("   Testing different chunk sizes with Blosc-Zstd compression")

output_dir = pathlib.Path("data/output/chunking_benchmarks")
output_dir.mkdir(parents=True, exist_ok=True)

# Blosc-Zstd compressor
compressor = Blosc(cname="zstd", clevel=5, shuffle=Blosc.SHUFFLE)

results = []

# Test different chunk sizes
chunk_sizes = [16, 32, 64, 128]

print("\n   📦 Testing chunk sizes: 16³, 32³, 64³, 128³")

for chunk_size in chunk_sizes:
    chunks = (chunk_size, chunk_size, chunk_size)
    store_path = output_dir / f"chunks_{chunk_size}.zarr"

    print(f"\n   Testing chunk {chunk_size}³...")
    result = benchmark_chunk_config(
        f"chunk_{chunk_size}", real_data, store_path, chunks, compressor
    )
    results.append(result)

    print(f"      Write: {result['write_time']:.3f}s")
    print(f"      Read (full): {result['read_time_full']:.3f}s")
    print(f"      Read (chunk): {result['read_time_chunk']:.4f}s")
    print(f"      Read (slice): {result['read_time_slice']:.4f}s")
    print(f"      Files: {result['file_count']}, Chunks: {result['chunk_count']}")
    print(
        f"      Storage: {result['storage_mb']:.2f} MB, Ratio: {result['compression_ratio']:.2f}x"
    )

# ============================================================================
# 4. TEST NON-CUBIC CHUNKS (OPTIMIZED FOR SLICE ACCESS)
# ============================================================================
print("\n   📦 Testing non-cubic chunks optimized for XY slice access...")

# Optimized for XY slicing (thin in Z direction)
non_cubic_configs = [
    ("slice_xy_64x64x16", (16, 64, 64)),  # Good for XY slicing
    ("slice_xy_128x128x16", (16, 128, 128)),  # Better for larger XY slices
    ("slice_xz_64x16x64", (64, 16, 64)),  # Good for XZ slicing
]

for name, chunks in non_cubic_configs:
    store_path = output_dir / f"{name}.zarr"
    print(f"\n   Testing {name} (shape {chunks})...")

    result = benchmark_chunk_config(name, real_data, store_path, chunks, compressor)
    results.append(result)

    print(f"      Write: {result['write_time']:.3f}s")
    print(f"      Read (full): {result['read_time_full']:.3f}s")
    print(f"      Read (slice): {result['read_time_slice']:.4f}s")
    print(f"      Files: {result['file_count']}, Chunks: {result['chunk_count']}")

# ============================================================================
# 5. RESULTS ANALYSIS
# ============================================================================
print("\n" + "=" * 80)
print("📊 CHUNKING BENCHMARK RESULTS")
print("=" * 80)

df = pd.DataFrame(results)
df_display = df[
    [
        "name",
        "chunks_shape",
        "write_time",
        "read_time_full",
        "read_time_chunk",
        "read_time_slice",
        "chunk_count",
        "file_count",
        "storage_mb",
        "compression_ratio",
    ]
].round(4)

print("\n" + df_display.to_string(index=False))

# Save results
csv_path = output_dir / "chunking_results.csv"
df.to_csv(csv_path, index=False)
print(f"\n✓ Results saved to: {csv_path}")

# ============================================================================
# 6. KEY INSIGHTS
# ============================================================================
print("\n" + "=" * 80)
print("🔍 KEY INSIGHTS")
print("=" * 80)

# File/chunk count analysis
cubic_data = df[df["name"].str.startswith("chunk_")]
print("\n📁 File Count by Chunk Size (cubic chunks):")
for _, row in cubic_data.iterrows():
    print(
        f"   {row['chunks_shape']:8s}: {row['chunk_count']:4.0f} chunks, "
        f"{row['file_count']:4.0f} total files"
    )

# Find best configurations
print("\n🏆 Best Performers:")
print(f"   Fastest write: {df.loc[df['write_time'].idxmin(), 'name']}")
print(f"   Fastest full read: {df.loc[df['read_time_full'].idxmin(), 'name']}")
print(f"   Fastest chunk read: {df.loc[df['read_time_chunk'].idxmin(), 'name']}")
print(f"   Fastest slice read: {df.loc[df['read_time_slice'].idxmin(), 'name']}")
print(
    f"   Fewest files: {df.loc[df['file_count'].idxmin(), 'name']} "
    f"({df['file_count'].min():.0f} files)"
)
print(
    f"   Best compression: {df.loc[df['compression_ratio'].idxmax(), 'name']} "
    f"({df['compression_ratio'].max():.2f}x)"
)

# Chunk size vs file count trade-off
print("\n📉 Chunk Size Trade-offs:")
smallest_chunk = cubic_data.iloc[0]
largest_chunk = cubic_data.iloc[-1]
file_reduction = (
    1 - largest_chunk["chunk_count"] / smallest_chunk["chunk_count"]
) * 100
read_overhead = (
    largest_chunk["read_time_chunk"] / smallest_chunk["read_time_chunk"] - 1
) * 100

print(
    f"   Going from {smallest_chunk['chunks_shape']} to {largest_chunk['chunks_shape']}:"
)
print(f"   - Reduces chunks by {file_reduction:.1f}%")
print(f"   - Increases single-chunk read time by {read_overhead:.1f}%")

# ============================================================================
# 7. VISUALIZATION
# ============================================================================
print("\n📈 Generating comparison plots...")

fig, axes = plt.subplots(2, 3, figsize=(18, 12))
fig.suptitle(
    "Zarr Chunking Benchmark - CryoET Data (Zarr v2)", fontsize=16, fontweight="bold"
)

# Plot 1: Write Performance vs Chunk Size
ax = axes[0, 0]
cubic_only = df[df["name"].str.startswith("chunk_")]
ax.plot(
    cubic_only["chunk_size"],
    cubic_only["write_time"],
    "o-",
    linewidth=2,
    markersize=10,
    color="steelblue",
)
ax.set_xlabel("Chunk Size (voxels per dimension)")
ax.set_ylabel("Write Time (s)")
ax.set_title("Write Performance vs Chunk Size")
ax.grid(True, alpha=0.3)

# Plot 2: Read Performance Comparison
ax = axes[0, 1]
x = range(len(cubic_only))
width = 0.25
ax.bar(
    [i - width for i in x],
    cubic_only["read_time_full"],
    width,
    label="Full Read",
    color="coral",
)
ax.bar(
    x, cubic_only["read_time_chunk"], width, label="Single Chunk", color="lightgreen"
)
ax.bar(
    [i + width for i in x],
    cubic_only["read_time_slice"],
    width,
    label="Single Slice",
    color="plum",
)
ax.set_xlabel("Chunk Size")
ax.set_ylabel("Time (s)")
ax.set_title("Read Performance by Operation Type")
ax.set_xticks(x)
ax.set_xticklabels([f"{int(s)}³" for s in cubic_only["chunk_size"]])
ax.legend()
ax.grid(True, alpha=0.3, axis="y")

# Plot 3: File/Chunk Count
ax = axes[0, 2]
ax.semilogy(
    cubic_only["chunk_size"],
    cubic_only["chunk_count"],
    "o-",
    linewidth=2,
    markersize=10,
    color="darkgreen",
    label="Data Chunks",
)
ax.semilogy(
    cubic_only["chunk_size"],
    cubic_only["file_count"],
    "s--",
    linewidth=2,
    markersize=8,
    color="darkred",
    label="Total Files",
)
ax.set_xlabel("Chunk Size (voxels per dimension)")
ax.set_ylabel("Count (log scale)")
ax.set_title("File/Chunk Count vs Chunk Size")
ax.legend()
ax.grid(True, alpha=0.3, which="both")

# Plot 4: Compression Ratio
ax = axes[1, 0]
ax.bar(df["name"], df["compression_ratio"], color="green", alpha=0.6)
ax.set_ylabel("Compression Ratio")
ax.set_title("Compression Ratio by Configuration")
ax.tick_params(axis="x", rotation=90)
ax.grid(True, alpha=0.3, axis="y")
ax.axhline(y=1.0, color="r", linestyle="--", alpha=0.3)

# Plot 5: Storage Size
ax = axes[1, 1]
ax.bar(df["name"], df["storage_mb"], color="purple", alpha=0.6)
ax.set_ylabel("Storage Size (MB)")
ax.set_title("Storage Size by Configuration")
ax.tick_params(axis="x", rotation=90)
ax.grid(True, alpha=0.3, axis="y")

# Plot 6: Efficiency Analysis (chunk read time vs file count)
ax = axes[1, 2]
ax.scatter(
    cubic_only["chunk_count"],
    cubic_only["read_time_chunk"] * 1000,
    s=200,
    alpha=0.6,
    c=cubic_only["chunk_size"],
    cmap="viridis",
)
for _, row in cubic_only.iterrows():
    ax.annotate(
        f"{int(row['chunk_size'])}³",
        (row["chunk_count"], row["read_time_chunk"] * 1000),
        fontsize=10,
        ha="center",
    )
ax.set_xlabel("Number of Chunks")
ax.set_ylabel("Single Chunk Read Time (ms)")
ax.set_title("Read Performance vs Storage Overhead")
ax.set_xscale("log")
ax.grid(True, alpha=0.3)

plt.tight_layout()
plot_path = output_dir / "chunking_comparison.png"
plt.savefig(plot_path, dpi=150, bbox_inches="tight")
print(f"✓ Plot saved to: {plot_path}")
plt.close()

# ============================================================================
# 8. RECOMMENDATIONS
# ============================================================================
print("\n" + "=" * 80)
print("💡 RECOMMENDATIONS FOR CRYOET DATA")
print("=" * 80)

print("\n🎯 For General Use (Balanced):")
print("   Recommended: Chunk size 64³")
print("   Why: Good balance of file count, read performance, and flexibility")
print(
    f"   Result: ~{cubic_data[cubic_data['chunk_size'] == 64].iloc[0]['chunk_count']:.0f} chunks for 128³ volume"
)

print("\n🎯 For XY Slice Viewing (Common in CryoET):")
print("   Recommended: Chunks (16, 128, 128) or (16, 64, 64)")
print("   Why: Thin in Z, matches slice access pattern")
print("   Result: Faster slice reads, minimal wasted I/O")

print("\n🎯 For Full Volume Processing:")
print("   Recommended: Chunk size 128³ (or match processing block size)")
print("   Why: Minimal chunk overhead, fastest for sequential access")
print("   Result: Fewest files, fastest full reads")

print("\n🎯 For Cloud Storage (S3, GCS, Azure):")
print("   Recommended: Chunk size 64³ or larger")
print("   Why: Reduces file count, fewer API calls, lower latency")
print("   Note: Consider Zarr v3 with sharding for even better performance")
print(
    f"   Current: ~{cubic_data[cubic_data['chunk_size'] == 64].iloc[0]['chunk_count']:.0f} files"
)
print("   With v3 sharding: Could reduce to <10 files (see sharding note below)")

print("\n🎯 For Random Access (ROI Extraction):")
print("   Recommended: Chunk size 32³ or 64³")
print("   Why: Small enough for targeted reads, not too many files")
print("   Result: Read only needed chunks, good cache utilization")

# ============================================================================
# 9. ZARR V3 SHARDING NOTE
# ============================================================================
print("\n" + "=" * 80)
print("🚀 ZARR V3 SHARDING - THE NEXT LEVEL")
print("=" * 80)

print("\n⚠️  Current Environment: Zarr v2.18.7 (for vizarr compatibility)")
print("    Zarr v2 limitation: Each chunk = 1 file")
print(
    f"    Example: 64³ chunks = ~{cubic_data[cubic_data['chunk_size'] == 64].iloc[0]['chunk_count']:.0f} files"
)

print("\n✨ Zarr v3 with Sharding:")
print("    - Multiple chunks can be stored in a single 'shard' file")
print("    - Example: 32³ chunks inside 128³ shards = ~1 file for our 128³ volume")
print("    - Reduces file count by 90%+ for cloud storage")
print("    - Maintains fine-grained read access")

print("\n📝 To test Zarr v3 sharding:")
print("    1. Create a new environment (zarr v3 is incompatible with vizarr)")
print("    2. Install: pip install zarr>=3.0.0")
print("    3. Run: python cryoet_sharding_benchmark_v3.py (see script)")

print("\n🔗 More info:")
print("    - Zarr v3 docs: https://zarr.readthedocs.io/en/v3.0.0/")
print("    - Sharding ZEP: https://zarr.dev/zeps/accepted/ZEP0002.html")

print("\n" + "=" * 80)
print("✅ CHUNKING BENCHMARK COMPLETE!")
print("=" * 80)
print(f"\nResults: {csv_path}")
print(f"Plot: {plot_path}")
print(f"Data: {output_dir}/")
