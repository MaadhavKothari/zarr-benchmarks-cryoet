#!/usr/bin/env python3
"""
CryoET Advanced Benchmark - Inspired by BioImageTools
Incorporates best practices:
- Multiple runs per configuration (statistical validation)
- Concurrent access patterns (threaded reads)
- Comprehensive statistical analysis (min/max/mean/std)
- Pandas DataFrame for organized results
- Error bars in visualizations
"""

import numpy as np
import pathlib
import time
import pandas as pd
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor
from cryoet_data_portal import Client, Dataset
import s3fs
import zarr
from numcodecs import Blosc
from zarr_benchmarks import utils
from typing import Dict, List, Tuple
import json

print("=" * 80)
print("CRYOET ADVANCED BENCHMARK (Statistical Validation)")
print("Inspired by: github.com/BioImageTools/zarr-chunk-benchmarking")
print("=" * 80)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Benchmark parameters
N_RUNS = 3  # Number of runs per configuration
N_THREADS = 4  # Concurrent read threads
RANDOM_SEED = 42

# Chunk configurations to test (systematic sweep)
CHUNK_CONFIGS = [
    (16, 16, 16),
    (32, 32, 32),
    (64, 64, 64),
    (128, 128, 128),
    # Non-cubic optimized for slicing
    (16, 64, 64),
    (16, 128, 128),
    (32, 64, 64),
]

# Compression methods
COMPRESSION_CONFIGS = [
    ("blosc_zstd_5", Blosc(cname="zstd", clevel=5, shuffle=Blosc.SHUFFLE)),
    ("blosc_lz4_3", Blosc(cname="lz4", clevel=3, shuffle=Blosc.SHUFFLE)),
    ("no_compression", None),
]

print(f"\n⚙️  Configuration:")
print(f"   Runs per test: {N_RUNS}")
print(f"   Concurrent threads: {N_THREADS}")
print(f"   Chunk configs: {len(CHUNK_CONFIGS)}")
print(f"   Compression methods: {len(COMPRESSION_CONFIGS)}")
print(f"   Total tests: {len(CHUNK_CONFIGS) * len(COMPRESSION_CONFIGS) * N_RUNS}")

# ============================================================================
# 1. DOWNLOAD CRYOET DATA
# ============================================================================
print("\n📡 1. Downloading CryoET data...")
client = Client()
dataset = Dataset.get_by_id(client, 10445)

runs = list(dataset.runs)
first_run = runs[0]
tomograms = list(first_run.tomograms)
first_tomo = tomograms[0]

s3 = s3fs.S3FileSystem(anon=True)
zarr_path = first_tomo.s3_omezarr_dir.replace("s3://", "")
store = s3fs.S3Map(root=zarr_path, s3=s3, check=False)
zarr_group = zarr.open(store, mode="r")
zarr_array = zarr_group["0"]

# Download 128³ subset
z_c, y_c, x_c = zarr_array.shape[0] // 2, zarr_array.shape[1] // 2, zarr_array.shape[2] // 2
size = 128

real_data = np.array(
    zarr_array[
        max(0, z_c - size // 2) : min(zarr_array.shape[0], z_c + size // 2),
        max(0, y_c - size // 2) : min(zarr_array.shape[1], y_c + size // 2),
        max(0, x_c - size // 2) : min(zarr_array.shape[2], x_c + size // 2),
    ]
)

print(f"   ✓ Downloaded {real_data.shape}, {real_data.nbytes / (1024**2):.2f} MB")

# ============================================================================
# 2. BENCHMARK FUNCTIONS
# ============================================================================


def benchmark_write_multi_run(
    data: np.ndarray,
    store_path: pathlib.Path,
    chunks: Tuple[int, int, int],
    compressor,
    n_runs: int = N_RUNS,
) -> Dict[str, float]:
    """Benchmark write with multiple runs for statistical validation."""
    times = []

    for run in range(n_runs):
        utils.remove_output_dir(store_path)

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
        elapsed = time.time() - t0
        times.append(elapsed)

    return {
        "mean": np.mean(times),
        "std": np.std(times),
        "min": np.min(times),
        "max": np.max(times),
        "times": times,
    }


def benchmark_read_full_multi_run(
    store_path: pathlib.Path, n_runs: int = N_RUNS
) -> Dict[str, float]:
    """Benchmark full read with multiple runs."""
    times = []

    for run in range(n_runs):
        zarr_arr = zarr.open_array(store_path, mode="r")

        t0 = time.time()
        _ = zarr_arr[:]
        elapsed = time.time() - t0
        times.append(elapsed)

    return {
        "mean": np.mean(times),
        "std": np.std(times),
        "min": np.min(times),
        "max": np.max(times),
        "times": times,
    }


def benchmark_read_slices_concurrent(
    store_path: pathlib.Path, n_slices: int = 10, n_threads: int = N_THREADS
) -> Dict[str, float]:
    """Benchmark concurrent slice reads (simulates real usage)."""
    zarr_arr = zarr.open_array(store_path, mode="r")

    # Random slice positions
    np.random.seed(RANDOM_SEED)
    slice_positions = np.random.randint(0, zarr_arr.shape[0], n_slices)

    def read_slice(z_pos):
        t0 = time.time()
        _ = zarr_arr[z_pos, :, :]
        return time.time() - t0

    # Sequential baseline
    t0 = time.time()
    sequential_times = [read_slice(z) for z in slice_positions]
    sequential_total = time.time() - t0

    # Concurrent reads
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=n_threads) as executor:
        concurrent_times = list(executor.map(read_slice, slice_positions))
    concurrent_total = time.time() - t0

    return {
        "sequential_mean": np.mean(sequential_times),
        "sequential_total": sequential_total,
        "concurrent_mean": np.mean(concurrent_times),
        "concurrent_total": concurrent_total,
        "speedup": sequential_total / concurrent_total,
    }


def benchmark_random_access(store_path: pathlib.Path, n_accesses: int = 20) -> Dict[str, float]:
    """Benchmark random small region access (ROI extraction pattern)."""
    zarr_arr = zarr.open_array(store_path, mode="r")

    np.random.seed(RANDOM_SEED)
    times = []

    roi_size = 32  # 32³ ROI

    for _ in range(n_accesses):
        # Random position
        z = np.random.randint(0, max(1, zarr_arr.shape[0] - roi_size))
        y = np.random.randint(0, max(1, zarr_arr.shape[1] - roi_size))
        x = np.random.randint(0, max(1, zarr_arr.shape[2] - roi_size))

        t0 = time.time()
        _ = zarr_arr[z : z + roi_size, y : y + roi_size, x : x + roi_size]
        times.append(time.time() - t0)

    return {
        "mean": np.mean(times),
        "std": np.std(times),
        "min": np.min(times),
        "max": np.max(times),
        "times": times,
    }


# ============================================================================
# 3. RUN COMPREHENSIVE BENCHMARKS
# ============================================================================
print("\n🔬 2. Running comprehensive benchmarks...")
print(
    f"   This will take ~{len(CHUNK_CONFIGS) * len(COMPRESSION_CONFIGS) * N_RUNS * 2 // 60} minutes"
)

output_dir = pathlib.Path("data/output/advanced_benchmarks")
output_dir.mkdir(parents=True, exist_ok=True)

results = []

for comp_name, compressor in COMPRESSION_CONFIGS:
    print(f"\n📦 Testing compression: {comp_name}")

    for chunks in CHUNK_CONFIGS:
        chunk_label = f"{chunks[0]}x{chunks[1]}x{chunks[2]}"
        print(f"   Chunks {chunk_label}...", end=" ", flush=True)

        store_path = output_dir / f"{comp_name}_{chunk_label}.zarr"

        # Write benchmarks (multiple runs)
        write_stats = benchmark_write_multi_run(real_data, store_path, chunks, compressor)
        print(f"W:{write_stats['mean']:.3f}±{write_stats['std']:.3f}s", end=" ", flush=True)

        # Read benchmarks (multiple runs)
        read_full_stats = benchmark_read_full_multi_run(store_path)
        print(f"R:{read_full_stats['mean']:.3f}±{read_full_stats['std']:.3f}s", end=" ", flush=True)

        # Concurrent slice reads
        slice_stats = benchmark_read_slices_concurrent(store_path)
        print(f"S:{slice_stats['concurrent_mean']*1000:.1f}ms", end=" ", flush=True)

        # Random access
        random_stats = benchmark_random_access(store_path)
        print(f"ROI:{random_stats['mean']*1000:.1f}ms", end=" ")

        # Storage metrics
        storage_size = utils.get_directory_size(store_path) / (1024**2)
        compression_ratio = real_data.nbytes / (storage_size * 1024**2)
        file_count = len(list(store_path.rglob("*")))

        print(f"[{file_count} files, {compression_ratio:.2f}x]")

        # Store results
        results.append(
            {
                "compression": comp_name,
                "chunk_z": chunks[0],
                "chunk_y": chunks[1],
                "chunk_x": chunks[2],
                "chunk_label": chunk_label,
                # Write stats
                "write_mean": write_stats["mean"],
                "write_std": write_stats["std"],
                "write_min": write_stats["min"],
                "write_max": write_stats["max"],
                # Read full stats
                "read_full_mean": read_full_stats["mean"],
                "read_full_std": read_full_stats["std"],
                "read_full_min": read_full_stats["min"],
                "read_full_max": read_full_stats["max"],
                # Slice stats
                "slice_sequential_mean": slice_stats["sequential_mean"],
                "slice_concurrent_mean": slice_stats["concurrent_mean"],
                "slice_speedup": slice_stats["speedup"],
                # Random access stats
                "random_mean": random_stats["mean"],
                "random_std": random_stats["std"],
                "random_min": random_stats["min"],
                "random_max": random_stats["max"],
                # Storage
                "storage_mb": storage_size,
                "compression_ratio": compression_ratio,
                "file_count": file_count,
            }
        )

# ============================================================================
# 4. CREATE RESULTS DATAFRAME
# ============================================================================
print("\n📊 3. Analyzing results...")

df = pd.DataFrame(results)

# Save detailed results
csv_path = output_dir / "advanced_benchmark_results.csv"
df.to_csv(csv_path, index=False)
print(f"   ✓ Saved to: {csv_path}")

# Save summary statistics
summary_path = output_dir / "benchmark_summary.json"
summary = {
    "n_runs": N_RUNS,
    "n_threads": N_THREADS,
    "total_configs": len(results),
    "best_write": df.loc[df["write_mean"].idxmin()].to_dict(),
    "best_read": df.loc[df["read_full_mean"].idxmin()].to_dict(),
    "best_compression": df.loc[df["compression_ratio"].idxmax()].to_dict(),
    "best_concurrent": df.loc[df["slice_speedup"].idxmax()].to_dict(),
}

with open(summary_path, "w") as f:
    json.dump(summary, f, indent=2)

# ============================================================================
# 5. ADVANCED VISUALIZATIONS WITH ERROR BARS
# ============================================================================
print("\n📈 4. Creating visualizations...")

fig = plt.figure(figsize=(20, 12))
fig.suptitle("Advanced CryoET Benchmarks - Statistical Validation", fontsize=16, fontweight="bold")

# Group by compression for comparison
for idx, comp_name in enumerate(["blosc_zstd_5", "blosc_lz4_3", "no_compression"]):
    df_comp = df[df["compression"] == comp_name]

    # Plot 1: Write performance with error bars
    ax = plt.subplot(3, 3, idx * 3 + 1)
    x = range(len(df_comp))
    ax.errorbar(
        x,
        df_comp["write_mean"],
        yerr=[
            df_comp["write_mean"] - df_comp["write_min"],
            df_comp["write_max"] - df_comp["write_mean"],
        ],
        fmt="o-",
        capsize=5,
        capthick=2,
        label=comp_name,
    )
    ax.set_ylabel("Write Time (s)")
    ax.set_title(f"{comp_name}: Write Performance")
    ax.set_xticks(x)
    ax.set_xticklabels(df_comp["chunk_label"], rotation=45)
    ax.grid(True, alpha=0.3)

    # Plot 2: Read performance with error bars
    ax = plt.subplot(3, 3, idx * 3 + 2)
    ax.errorbar(
        x,
        df_comp["read_full_mean"],
        yerr=[
            df_comp["read_full_mean"] - df_comp["read_full_min"],
            df_comp["read_full_max"] - df_comp["read_full_mean"],
        ],
        fmt="s-",
        capsize=5,
        capthick=2,
        color="orange",
    )
    ax.set_ylabel("Read Time (s)")
    ax.set_title(f"{comp_name}: Read Performance")
    ax.set_xticks(x)
    ax.set_xticklabels(df_comp["chunk_label"], rotation=45)
    ax.grid(True, alpha=0.3)

    # Plot 3: Concurrent vs Sequential
    ax = plt.subplot(3, 3, idx * 3 + 3)
    width = 0.35
    x_pos = np.arange(len(df_comp))
    ax.bar(
        x_pos - width / 2,
        df_comp["slice_sequential_mean"] * 1000,
        width,
        label="Sequential",
        alpha=0.8,
    )
    ax.bar(
        x_pos + width / 2,
        df_comp["slice_concurrent_mean"] * 1000,
        width,
        label=f"Concurrent ({N_THREADS}T)",
        alpha=0.8,
    )
    ax.set_ylabel("Slice Read Time (ms)")
    ax.set_title(f"{comp_name}: Concurrency Speedup")
    ax.set_xticks(x_pos)
    ax.set_xticklabels(df_comp["chunk_label"], rotation=45)
    ax.legend()
    ax.grid(True, alpha=0.3)

plt.tight_layout()
plot_path = output_dir / "advanced_benchmark_comparison.png"
plt.savefig(plot_path, dpi=150, bbox_inches="tight")
print(f"   ✓ Saved to: {plot_path}")
plt.close()

# ============================================================================
# 6. SPECIALIZED PLOTS
# ============================================================================

# Speedup analysis
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle("Concurrency & Access Pattern Analysis", fontsize=16, fontweight="bold")

# Plot 1: Concurrent speedup
ax = axes[0, 0]
for comp_name in df["compression"].unique():
    df_comp = df[df["compression"] == comp_name]
    ax.plot(df_comp["chunk_label"], df_comp["slice_speedup"], "o-", label=comp_name, markersize=8)
ax.axhline(y=1.0, color="r", linestyle="--", alpha=0.5, label="No speedup")
ax.set_xlabel("Chunk Configuration")
ax.set_ylabel("Speedup Factor")
ax.set_title(f"Concurrent Read Speedup ({N_THREADS} threads)")
ax.legend()
ax.grid(True, alpha=0.3)
ax.tick_params(axis="x", rotation=45)

# Plot 2: Random access performance
ax = axes[0, 1]
for comp_name in df["compression"].unique():
    df_comp = df[df["compression"] == comp_name]
    ax.errorbar(
        df_comp["chunk_label"],
        df_comp["random_mean"] * 1000,
        yerr=df_comp["random_std"] * 1000,
        fmt="o-",
        capsize=5,
        label=comp_name,
    )
ax.set_xlabel("Chunk Configuration")
ax.set_ylabel("Random Access Time (ms)")
ax.set_title("Random 32³ ROI Access")
ax.legend()
ax.grid(True, alpha=0.3)
ax.tick_params(axis="x", rotation=45)

# Plot 3: File count vs performance
ax = axes[1, 0]
scatter = ax.scatter(
    df["file_count"],
    df["read_full_mean"] * 1000,
    c=df["compression_ratio"],
    s=100,
    alpha=0.6,
    cmap="viridis",
)
ax.set_xlabel("File Count")
ax.set_ylabel("Full Read Time (ms)")
ax.set_title("File Count Impact on Performance")
ax.set_xscale("log")
plt.colorbar(scatter, ax=ax, label="Compression Ratio")
ax.grid(True, alpha=0.3)

# Plot 4: Compression vs Performance trade-off
ax = axes[1, 1]
for comp_name in df["compression"].unique():
    df_comp = df[df["compression"] == comp_name]
    ax.scatter(
        df_comp["compression_ratio"],
        df_comp["write_mean"],
        s=df_comp["file_count"],
        alpha=0.6,
        label=comp_name,
    )
ax.set_xlabel("Compression Ratio")
ax.set_ylabel("Write Time (s)")
ax.set_title("Compression vs Write Performance (size = file count)")
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
analysis_path = output_dir / "concurrency_analysis.png"
plt.savefig(analysis_path, dpi=150, bbox_inches="tight")
print(f"   ✓ Saved to: {analysis_path}")
plt.close()

# ============================================================================
# 7. STATISTICAL SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("📊 STATISTICAL SUMMARY")
print("=" * 80)

print(f"\n🔬 Test Configuration:")
print(f"   Runs per config: {N_RUNS}")
print(f"   Concurrent threads: {N_THREADS}")
print(f"   Total configs tested: {len(results)}")

print(f"\n🏆 Best Performers (mean ± std):")
best_write = df.loc[df["write_mean"].idxmin()]
print(f"   Fastest write: {best_write['compression']} {best_write['chunk_label']}")
print(f"      Time: {best_write['write_mean']:.3f} ± {best_write['write_std']:.3f}s")

best_read = df.loc[df["read_full_mean"].idxmin()]
print(f"   Fastest read: {best_read['compression']} {best_read['chunk_label']}")
print(f"      Time: {best_read['read_full_mean']:.3f} ± {best_read['read_full_std']:.3f}s")

best_concurrent = df.loc[df["slice_speedup"].idxmax()]
print(f"   Best concurrent: {best_concurrent['compression']} {best_concurrent['chunk_label']}")
print(f"      Speedup: {best_concurrent['slice_speedup']:.2f}×")

best_compression = df.loc[df["compression_ratio"].idxmax()]
print(f"   Best compression: {best_compression['compression']} {best_compression['chunk_label']}")
print(f"      Ratio: {best_compression['compression_ratio']:.2f}×")

print(f"\n📏 Performance Variability:")
print(f"   Write std/mean: {(df['write_std'] / df['write_mean']).mean() * 100:.1f}% (avg)")
print(f"   Read std/mean: {(df['read_full_std'] / df['read_full_mean']).mean() * 100:.1f}% (avg)")
print(
    f"   {'Low variability = consistent performance' if (df['write_std'] / df['write_mean']).mean() < 0.1 else 'High variability detected'}"
)

print("\n" + "=" * 80)
print("✅ ADVANCED BENCHMARK COMPLETE!")
print("=" * 80)
print(f"\nResults: {csv_path}")
print(f"Summary: {summary_path}")
print(f"Plots: {output_dir}/*.png")
print("\n💡 Key improvements over basic benchmark:")
print("   ✓ Statistical validation (3 runs per test)")
print("   ✓ Error bars show performance variance")
print("   ✓ Concurrent access patterns tested")
print("   ✓ Random ROI access simulated")
print("   ✓ Comprehensive Pandas DataFrame")
print("   ✓ JSON summary for automation")
