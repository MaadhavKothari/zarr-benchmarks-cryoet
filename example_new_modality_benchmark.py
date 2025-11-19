#!/usr/bin/env python3
"""
Example: Adding a New Imaging Modality Benchmark

This demonstrates how to extend the benchmarking system with a new modality.
In this example, we'll add "X-ray microtomography" benchmarking.
"""

import numpy as np
import time
from pathlib import Path

# Import the extensible framework
from zarr_benchmarks.dataset_types import (
    DatasetMetadata,
    DatasetType,
    BenchmarkConfig,
    CompressionProfile,
)
from multi_dataset_benchmark import DatasetBenchmarkRunner


def generate_xray_tomography_data(shape=(512, 512, 512)):
    """
    Generate synthetic X-ray microtomography data

    Characteristics:
    - Typically uint16 (12-16 bit detectors)
    - Contains both dense and porous materials
    - Ring artifacts and noise are common
    """
    print(f"Generating synthetic X-ray μCT data ({shape})...")

    # Base absorption (grayscale 0-4095 for 12-bit)
    data = np.random.randint(0, 500, shape, dtype=np.uint16)

    # Add dense particles (high absorption)
    num_particles = 100
    for _ in range(num_particles):
        center = [np.random.randint(50, s - 50) for s in shape]
        radius = np.random.randint(5, 20)

        z, y, x = np.ogrid[: shape[0], : shape[1], : shape[2]]
        mask = (
            (z - center[0]) ** 2 + (y - center[1]) ** 2 + (x - center[2]) ** 2
        ) < radius**2

        data[mask] = np.random.randint(2000, 4095)

    # Add porous matrix
    noise = np.random.randint(0, 1000, shape, dtype=np.uint16)
    data = np.clip(data + noise, 0, 4095)

    print(f"  Generated {data.nbytes / 1024**2:.1f} MB of data")
    return data


def create_xray_ct_metadata(
    shape, voxel_size=(2.0, 2.0, 2.0), source="synthetic"
):
    """
    Create metadata for X-ray microtomography dataset

    This is where you define your new modality's characteristics
    """
    return DatasetMetadata(
        name=f"xray_ct_{shape[0]}x{shape[1]}x{shape[2]}",
        dataset_type=DatasetType.CUSTOM,  # Use CUSTOM or add XRAY_CT to enum
        shape=shape,
        dtype=np.dtype(np.uint16),  # Typical for X-ray detectors
        voxel_size=voxel_size,
        units="um",  # micrometers
        channels=1,
        timepoints=1,
        z_slices=shape[0],
        source=source,
        modality_specific={
            "detector_type": "flat_panel",
            "energy": "80kV",  # X-ray tube voltage
            "exposure_time": "500ms",
            "projections": 1200,  # Number of angles
            "material": "composite",  # What was scanned
        },
    )


def run_xray_benchmark():
    """Run a complete benchmark for X-ray microtomography data"""

    print("=" * 70)
    print("X-RAY MICROTOMOGRAPHY ZARR BENCHMARKING")
    print("=" * 70)
    print()

    # Step 1: Generate or load data
    shape = (256, 256, 256)  # Smaller for demo, real scans are often 2048^3
    data = generate_xray_tomography_data(shape)

    # Step 2: Create metadata
    metadata = create_xray_ct_metadata(
        shape=shape,
        voxel_size=(2.0, 2.0, 2.0),  # 2 micron resolution
        source="synthetic_demo",
    )

    print(f"\nDataset Information:")
    print(f"  Name: {metadata.name}")
    print(f"  Type: {metadata.dataset_type.value}")
    print(f"  Shape: {metadata.shape}")
    print(f"  Size: {metadata.total_size_mb:.2f} MB")
    print(f"  Suggested compression: {metadata.suggest_compression()}")

    # Step 3: Test different compression profiles
    profiles_to_test = {
        "archival": CompressionProfile.ARCHIVAL,  # For long-term storage
        "balanced": CompressionProfile.BALANCED,  # General use
        "fast": CompressionProfile.FAST,  # Interactive viewing
    }

    all_results = {}

    for profile_name, profile in profiles_to_test.items():
        print(f"\n{'='*70}")
        print(f"Testing Profile: {profile_name.upper()}")
        print("=" * 70)

        # Configure benchmark
        config = BenchmarkConfig(
            dataset_metadata=metadata,
            compression_profile=profile,
            codecs_to_test=[
                "blosc_zstd",  # Best compression
                "blosc_lz4",  # Fastest
                "zstd",  # Good balance
            ],
            num_runs=3,  # Average over 3 runs
            output_dir=f"data/output/xray_benchmarks/{profile_name}",
            save_results=True,
        )

        # Get suggested chunk sizes for this profile
        suggested_chunks = metadata.suggest_chunk_size(compression_profile=profile)
        print(f"\nSuggested chunk size: {suggested_chunks}")

        # Run benchmark
        runner = DatasetBenchmarkRunner(config)
        print("\nRunning benchmarks...")
        results = runner.run(data)

        # Store results
        all_results[profile_name] = results

        # Display results
        print(f"\nResults for {profile_name}:")
        print(f"  Best write performance:")
        print(
            f"    {results['best_write']['codec']}: {results['best_write']['time_s']:.3f}s "
            f"({results['best_write']['throughput_mbs']:.1f} MB/s)"
        )
        print(f"  Best read performance:")
        print(
            f"    {results['best_read']['codec']}: {results['best_read']['time_s']:.3f}s "
            f"({results['best_read']['throughput_mbs']:.1f} MB/s)"
        )
        print(f"  Best compression:")
        print(
            f"    {results['best_compression']['codec']}: {results['best_compression']['ratio']:.2f}× "
            f"({results['best_compression']['size_mb']:.2f} MB)"
        )

    # Step 4: Summary and recommendations
    print(f"\n{'='*70}")
    print("BENCHMARK SUMMARY & RECOMMENDATIONS")
    print("=" * 70)

    print("\n📊 Profile Comparison:")
    for profile_name, results in all_results.items():
        savings = (
            1 - results["best_compression"]["size_mb"] / metadata.total_size_mb
        ) * 100
        print(f"\n  {profile_name.upper()}:")
        print(f"    Best codec: {results['best_compression']['codec']}")
        print(f"    Size reduction: {savings:.1f}%")
        print(f"    Read speed: {results['best_read']['throughput_mbs']:.0f} MB/s")

    print("\n💡 Recommendations:")
    print("  • For archival storage: Use blosc_zstd for maximum compression")
    print("  • For active analysis: Use blosc_lz4 for fast read/write")
    print("  • For sharing: Use balanced profile for good compromise")

    print(f"\n✓ Results saved to data/output/xray_benchmarks/")


def demo_webhook_integration():
    """
    Demonstrate how to integrate this new modality with the webhook server

    This would be used in your X-ray acquisition pipeline
    """
    print("\n" + "=" * 70)
    print("WEBHOOK INTEGRATION EXAMPLE")
    print("=" * 70)

    webhook_config = {
        "dataset": {
            "name": "xray_sample_001",
            "type": "custom",  # Use 'custom' or add 'xray_ct' to the enum
            "shape": [512, 512, 512],
            "dtype": "uint16",
            "voxel_size": [2.0, 2.0, 2.0],
        },
        "benchmark": {
            "codecs": ["blosc_zstd", "blosc_lz4", "zstd"],
            "compression_profile": "balanced",
            "num_runs": 3,
        },
    }

    print("\nTo submit via webhook, POST this JSON to the server:")
    print("\ncurl -X POST http://localhost:8080/webhook/benchmark \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '", end="")
    import json

    print(json.dumps(webhook_config, indent=2), end="")
    print("'")

    print("\nOr in Python:")
    print("""
import requests

response = requests.post(
    'http://localhost:8080/webhook/benchmark',
    json=webhook_config
)

job_id = response.json()['job_id']
print(f"Job submitted: {job_id}")
""")


if __name__ == "__main__":
    # Run the benchmark
    run_xray_benchmark()

    # Show webhook integration
    demo_webhook_integration()

    print("\n" + "=" * 70)
    print("✅ DEMO COMPLETE!")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Check results in data/output/xray_benchmarks/")
    print("  2. Adapt this script for your specific modality")
    print("  3. Add your modality to dataset_types.py")
    print("  4. See EXTENDING_BENCHMARKS.md for more details")
