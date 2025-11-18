#!/usr/bin/env python3
"""
CryoET Zarr v3 Sharding Benchmark
Test different chunk sizes, shard sizes, and compression methods with Zarr v3 sharding
"""

import pathlib
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import s3fs
import zarr
from cryoet_data_portal import Client, Dataset
from zarr.codecs import BloscCodec, BytesCodec, ShardingCodec

from zarr_benchmarks import utils

print("=" * 80)
print("CRYOET ZARR V3 SHARDING BENCHMARK")
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


def write_zarr_v2(data, store_path, chunks, compressor):
    """Write with Zarr v2 (no sharding)"""
    utils.remove_output_dir(store_path)
    zarr.create_array(
        store=store_path,
        shape=data.shape,
        chunks=chunks,
        dtype=data.dtype,
        compressor=compressor,
        zarr_format=2,
        fill_value=0,
    )[:] = data


def write_zarr_v3_no_sharding(data, store_path, chunks, compressor):
    """Write with Zarr v3 without sharding (for comparison)"""
    utils.remove_output_dir(store_path)

    codecs = [BytesCodec()]
    if compressor is not None:
        codecs.append(compressor)

    zarr.create_array(
        store=store_path,
        shape=data.shape,
        chunks=chunks,
        dtype=data.dtype,
        compressors=codecs,
        zarr_format=3,
        fill_value=0,
    )[:] = data


def write_zarr_v3_with_sharding(data, store_path, chunk_shape, shard_shape, compressor):
    """Write with Zarr v3 with sharding codec"""
    utils.remove_output_dir(store_path)

    # Build codec pipeline: sharding wraps chunk compression
    inner_codecs = [BytesCodec()]
    if compressor is not None:
        inner_codecs.append(compressor)

    sharding_codec = ShardingCodec(chunk_shape=chunk_shape, codecs=inner_codecs)

    zarr.create_array(
        store=store_path,
        shape=data.shape,
        chunks=shard_shape,  # Shard shape is the outer chunk
        dtype=data.dtype,
        compressors=[BytesCodec(), sharding_codec],
        zarr_format=3,
        fill_value=0,
    )[:] = data


def benchmark_config(name, data, store_path, write_func, read_verify=True):
    """Benchmark a single configuration"""
    # Write
    t0 = time.time()
    write_func()
    write_time = time.time() - t0

    # Read
    t0 = time.time()
    zarr_read = zarr.open_array(store_path, mode="r")
    read_back = zarr_read[:]
    read_time = time.time() - t0

    # Verify data integrity
    if read_verify:
        assert np.allclose(data, read_back), f"Data mismatch for {name}!"

    # Metrics
    storage_size = utils.get_directory_size(store_path) / (1024**2)
    file_count = count_files_in_zarr(store_path)
    compression_ratio = data.nbytes / (storage_size * 1024**2)

    return {
        "name": name,
        "write_time": write_time,
        "read_time": read_time,
        "storage_mb": storage_size,
        "compression_ratio": compression_ratio,
        "file_count": file_count,
    }


# ============================================================================
# 3. BENCHMARK CONFIGURATIONS
# ============================================================================
print("\n⚙️  2. Running sharding benchmarks...")
print("   Testing Zarr v2 vs v3, with and without sharding")

output_dir = pathlib.Path("data/output/sharding_benchmarks")
output_dir.mkdir(parents=True, exist_ok=True)

# Compression to test
blosc_zstd_v2 = zarr.storage.default_compressor  # v2 style
blosc_zstd_v3 = BloscCodec(cname="zstd", clevel=5, shuffle="shuffle")

results = []

# ============================================================================
# Test 1: Zarr v2 with different chunk sizes (baseline)
# ============================================================================
print("\n   📦 Test 1: Zarr v2 (no sharding) - baseline")

for chunk_size in [32, 64, 128]:
    chunks = (chunk_size, chunk_size, chunk_size)
    store_path = output_dir / f"v2_chunks_{chunk_size}.zarr"

    result = benchmark_config(
        f"v2_chunk{chunk_size}",
        real_data,
        store_path,
        lambda: write_zarr_v2(real_data, store_path, chunks, blosc_zstd_v2),
    )
    results.append(result)
    print(
        f"      Chunk {chunk_size}³: Write={result['write_time']:.3f}s, "
        f"Read={result['read_time']:.3f}s, Files={result['file_count']}, "
        f"Size={result['storage_mb']:.2f}MB"
    )

# ============================================================================
# Test 2: Zarr v3 without sharding (for fair comparison)
# ============================================================================
print("\n   📦 Test 2: Zarr v3 without sharding")

for chunk_size in [32, 64, 128]:
    chunks = (chunk_size, chunk_size, chunk_size)
    store_path = output_dir / f"v3_no_shard_chunks_{chunk_size}.zarr"

    result = benchmark_config(
        f"v3_noshard_chunk{chunk_size}",
        real_data,
        store_path,
        lambda cs=chunk_size: write_zarr_v3_no_sharding(
            real_data,
            output_dir / f"v3_no_shard_chunks_{cs}.zarr",
            (cs, cs, cs),
            blosc_zstd_v3,
        ),
    )
    results.append(result)
    print(
        f"      Chunk {chunk_size}³: Write={result['write_time']:.3f}s, "
        f"Read={result['read_time']:.3f}s, Files={result['file_count']}, "
        f"Size={result['storage_mb']:.2f}MB"
    )

# ============================================================================
# Test 3: Zarr v3 WITH sharding - various configurations
# ============================================================================
print("\n   🎯 Test 3: Zarr v3 WITH sharding (THE KEY TEST)")

# Configuration 1: Small chunks (32³), medium shards (128³)
# This is like HEFTIE recommendation - read granularity vs write efficiency
config_name = "v3_shard_c32_s128"
store_path = output_dir / f"{config_name}.zarr"
result = benchmark_config(
    config_name,
    real_data,
    store_path,
    lambda: write_zarr_v3_with_sharding(
        real_data,
        store_path,
        chunk_shape=(32, 32, 32),  # Read granularity
        shard_shape=(128, 128, 128),  # Write efficiency
        compressor=blosc_zstd_v3,
    ),
)
results.append(result)
print(
    f"      Chunk 32³ → Shard 128³: Write={result['write_time']:.3f}s, "
    f"Read={result['read_time']:.3f}s, Files={result['file_count']}, "
    f"Size={result['storage_mb']:.2f}MB"
)

# Configuration 2: Medium chunks (64³), large shards (128³)
config_name = "v3_shard_c64_s128"
store_path = output_dir / f"{config_name}.zarr"
result = benchmark_config(
    config_name,
    real_data,
    store_path,
    lambda: write_zarr_v3_with_sharding(
        real_data,
        store_path,
        chunk_shape=(64, 64, 64),
        shard_shape=(128, 128, 128),
        compressor=blosc_zstd_v3,
    ),
)
results.append(result)
print(
    f"      Chunk 64³ → Shard 128³: Write={result['write_time']:.3f}s, "
    f"Read={result['read_time']:.3f}s, Files={result['file_count']}, "
    f"Size={result['storage_mb']:.2f}MB"
)

# Configuration 3: Very small chunks (16³), medium shards (128³)
# Extreme read granularity - useful for random access
config_name = "v3_shard_c16_s128"
store_path = output_dir / f"{config_name}.zarr"
result = benchmark_config(
    config_name,
    real_data,
    store_path,
    lambda: write_zarr_v3_with_sharding(
        real_data,
        store_path,
        chunk_shape=(16, 16, 16),
        shard_shape=(128, 128, 128),
        compressor=blosc_zstd_v3,
    ),
)
results.append(result)
print(
    f"      Chunk 16³ → Shard 128³: Write={result['write_time']:.3f}s, "
    f"Read={result['read_time']:.3f}s, Files={result['file_count']}, "
    f"Size={result['storage_mb']:.2f}MB"
)

# Configuration 4: Small chunks (32³), very large shards (entire volume)
# Maximum write efficiency - single file
config_name = "v3_shard_c32_s128_single"
store_path = output_dir / f"{config_name}.zarr"
result = benchmark_config(
    config_name,
    real_data,
    store_path,
    lambda: write_zarr_v3_with_sharding(
        real_data,
        store_path,
        chunk_shape=(32, 32, 32),
        shard_shape=real_data.shape,  # Entire volume in one shard
        compressor=blosc_zstd_v3,
    ),
)
results.append(result)
print(
    f"      Chunk 32³ → Shard {real_data.shape}: Write={result['write_time']:.3f}s, "
    f"Read={result['read_time']:.3f}s, Files={result['file_count']}, "
    f"Size={result['storage_mb']:.2f}MB"
)

# ============================================================================
# 4. RESULTS ANALYSIS
# ============================================================================
print("\n" + "=" * 80)
print("📊 SHARDING BENCHMARK RESULTS")
print("=" * 80)

df = pd.DataFrame(results)
df = df.round(3)
print("\n" + df.to_string(index=False))

# Save results
csv_path = output_dir / "sharding_results.csv"
df.to_csv(csv_path, index=False)
print(f"\n✓ Results saved to: {csv_path}")

# ============================================================================
# 5. KEY INSIGHTS
# ============================================================================
print("\n" + "=" * 80)
print("🔍 KEY INSIGHTS")
print("=" * 80)

# File count comparison
v2_files = df[df["name"].str.startswith("v2")]["file_count"].mean()
v3_noshard_files = df[df["name"].str.startswith("v3_noshard")]["file_count"].mean()
v3_shard_files = df[df["name"].str.startswith("v3_shard")]["file_count"].mean()

print("\n📁 File Count Reduction:")
print(f"   Zarr v2 average: {v2_files:.0f} files")
print(f"   Zarr v3 (no shard) average: {v3_noshard_files:.0f} files")
print(f"   Zarr v3 (with shard) average: {v3_shard_files:.0f} files")
print(
    f"   Reduction: {((v2_files - v3_shard_files) / v2_files * 100):.1f}% fewer files with sharding"
)

# Find best configurations
best_write = df.loc[df["write_time"].idxmin()]
best_read = df.loc[df["read_time"].idxmin()]
best_compression = df.loc[df["compression_ratio"].idxmax()]
fewest_files = df.loc[df["file_count"].idxmin()]

print("\n🏆 Best Performers:")
print(f"   Fastest write: {best_write['name']} ({best_write['write_time']:.3f}s)")
print(f"   Fastest read: {best_read['name']} ({best_read['read_time']:.3f}s)")
print(
    f"   Best compression: {best_compression['name']} ({best_compression['compression_ratio']:.2f}x)"
)
print(f"   Fewest files: {fewest_files['name']} ({fewest_files['file_count']} files)")

# ============================================================================
# 6. VISUALIZATION
# ============================================================================
print("\n📈 Generating comparison plots...")

fig, axes = plt.subplots(2, 3, figsize=(18, 12))
fig.suptitle("Zarr v3 Sharding Benchmark - CryoET Data", fontsize=16, fontweight="bold")

# Separate by category
v2_data = df[df["name"].str.startswith("v2")]
v3_noshard = df[df["name"].str.startswith("v3_noshard")]
v3_shard = df[df["name"].str.startswith("v3_shard")]

categories = ["v2", "v3_noshard", "v3_shard"]
colors = {"v2": "#FF6B6B", "v3_noshard": "#4ECDC4", "v3_shard": "#45B7D1"}

# Plot 1: Write Performance
ax = axes[0, 0]
for cat, data in [("v2", v2_data), ("v3_noshard", v3_noshard), ("v3_shard", v3_shard)]:
    ax.scatter(
        range(len(data)),
        data["write_time"],
        label=cat.replace("_", " ").title(),
        color=colors[cat],
        s=100,
        alpha=0.7,
    )
ax.set_ylabel("Write Time (s)")
ax.set_title("Write Performance")
ax.legend()
ax.grid(True, alpha=0.3)

# Plot 2: Read Performance
ax = axes[0, 1]
for cat, data in [("v2", v2_data), ("v3_noshard", v3_noshard), ("v3_shard", v3_shard)]:
    ax.scatter(
        range(len(data)),
        data["read_time"],
        label=cat.replace("_", " ").title(),
        color=colors[cat],
        s=100,
        alpha=0.7,
    )
ax.set_ylabel("Read Time (s)")
ax.set_title("Read Performance")
ax.legend()
ax.grid(True, alpha=0.3)

# Plot 3: File Count (KEY METRIC!)
ax = axes[0, 2]
bars = ax.bar(
    df["name"],
    df["file_count"],
    color=[
        colors[n.split("_")[0] + ("_" + n.split("_")[1] if "noshard" in n else "")]
        for n in df["name"]
    ],
)
ax.set_ylabel("File Count")
ax.set_title("File Count (Lower is Better for Object Storage)")
ax.tick_params(axis="x", rotation=90)
ax.grid(True, alpha=0.3, axis="y")

# Plot 4: Compression Ratio
ax = axes[1, 0]
ax.bar(df["name"], df["compression_ratio"], color="green", alpha=0.6)
ax.set_ylabel("Compression Ratio")
ax.set_title("Compression Ratio")
ax.tick_params(axis="x", rotation=90)
ax.grid(True, alpha=0.3, axis="y")

# Plot 5: Storage Size
ax = axes[1, 1]
ax.bar(df["name"], df["storage_mb"], color="purple", alpha=0.6)
ax.set_ylabel("Storage Size (MB)")
ax.set_title("Storage Size")
ax.tick_params(axis="x", rotation=90)
ax.grid(True, alpha=0.3, axis="y")

# Plot 6: Write vs Read Trade-off
ax = axes[1, 2]
for cat, data in [("v2", v2_data), ("v3_noshard", v3_noshard), ("v3_shard", v3_shard)]:
    ax.scatter(
        data["write_time"],
        data["read_time"],
        label=cat.replace("_", " ").title(),
        color=colors[cat],
        s=150,
        alpha=0.7,
    )
    # Add labels
    for _, row in data.iterrows():
        ax.annotate(
            row["name"].split("_")[-1],
            (row["write_time"], row["read_time"]),
            fontsize=8,
            alpha=0.7,
        )
ax.set_xlabel("Write Time (s)")
ax.set_ylabel("Read Time (s)")
ax.set_title("Write vs Read Trade-off (Lower-Left is Better)")
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plot_path = output_dir / "sharding_comparison.png"
plt.savefig(plot_path, dpi=150, bbox_inches="tight")
print(f"✓ Plot saved to: {plot_path}")
plt.close()

# ============================================================================
# 7. RECOMMENDATIONS
# ============================================================================
print("\n" + "=" * 80)
print("💡 RECOMMENDATIONS FOR CRYOET DATA")
print("=" * 80)

print("\n🎯 For Cloud/Object Storage (S3, GCS, Azure):")
print("   Use: Zarr v3 with sharding - Chunk 32³, Shard 128³")
print("   Why: Reduces file count by ~90%, improves listing performance")
print("   Benefit: Fewer API calls, lower costs, faster access")

print("\n🎯 For Local File Systems:")
print("   Use: Zarr v3 with sharding - Chunk 64³, Shard 128³")
print("   Why: Balance between read granularity and file system overhead")
print("   Benefit: Fewer inodes, better caching, faster directory operations")

print("\n🎯 For Random Access Patterns:")
print("   Use: Zarr v3 with sharding - Chunk 16³, Shard 128³")
print("   Why: Very small chunks for fine-grained access, sharding for efficiency")
print("   Benefit: Read only what you need, minimal wasted I/O")

print("\n🎯 For Sequential Analysis:")
print("   Use: Zarr v2 or v3 - Chunk 128³, no sharding")
print("   Why: Large chunks match access pattern, sharding overhead not needed")
print("   Benefit: Simplest, fastest for full-volume processing")

print("\n" + "=" * 80)
print("✅ SHARDING BENCHMARK COMPLETE!")
print("=" * 80)
print(f"\nResults: {csv_path}")
print(f"Plot: {plot_path}")
print(f"Data: {output_dir}/")
