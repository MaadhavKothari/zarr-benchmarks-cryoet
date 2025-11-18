#!/usr/bin/env python3
"""
Multi-Dataset Benchmark Orchestrator

Runs comprehensive benchmarks across multiple dataset types with webhook integration.
"""

import json
import pathlib
import time
from datetime import datetime
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from test_data_generator import generate_synthetic_volume
from zarr_benchmarks import utils
from zarr_benchmarks.dataset_types import (
    BenchmarkConfig,
    CompressionProfile,
    create_confocal_metadata,
    create_cryoet_metadata,
    create_lightsheet_metadata,
)
from zarr_benchmarks.read_write_zarr import read_write_zarr

print("=" * 80)
print("MULTI-DATASET BENCHMARK ORCHESTRATOR")
print("=" * 80)


class DatasetBenchmarkRunner:
    """Runs benchmarks for a specific dataset"""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.results: List[Dict[str, Any]] = []

    def run(self, data: np.ndarray) -> Dict[str, Any]:
        """Run benchmarks on dataset"""
        print(f"\n{'=' * 80}")
        print(f"Benchmarking: {self.config.dataset_metadata.name}")
        print(f"Type: {self.config.dataset_metadata.dataset_type.value}")
        print(f"Shape: {self.config.dataset_metadata.shape}")
        print(f"Size: {self.config.dataset_metadata.total_size_mb:.2f} MB")
        print(f"{'=' * 80}")

        output_dir = (
            pathlib.Path(self.config.output_dir) / self.config.dataset_metadata.name
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        all_results = []

        # Test each codec
        for codec in self.config.codecs_to_test:
            print(f"\n  Testing {codec}...")

            for chunks in self.config.chunk_sizes_to_test:
                results_for_run = []

                # Run multiple times for statistical significance
                for run_num in range(self.config.num_runs):
                    store_path = output_dir / f"{codec}_run{run_num}.zarr"
                    utils.remove_output_dir(store_path)

                    # Get compressor
                    if codec == "blosc_zstd":
                        compressor = read_write_zarr.get_blosc_compressor(
                            "zstd", 5, "shuffle"
                        )
                    elif codec == "blosc_lz4":
                        compressor = read_write_zarr.get_blosc_compressor(
                            "lz4", 5, "shuffle"
                        )
                    elif codec == "zstd":
                        compressor = read_write_zarr.get_zstd_compressor(5)
                    elif codec == "gzip":
                        compressor = read_write_zarr.get_gzip_compressor(6)
                    else:
                        compressor = None

                    # Write benchmark
                    t0 = time.time()
                    read_write_zarr.write_zarr_array(
                        data,
                        store_path,
                        overwrite=False,
                        chunks=chunks,
                        compressor=compressor,
                        zarr_spec=2,
                    )
                    write_time = time.time() - t0

                    # Read benchmark
                    t0 = time.time()
                    _ = read_write_zarr.read_zarr_array(store_path)
                    read_time = time.time() - t0

                    # Get metrics
                    size_mb = utils.get_directory_size(store_path) / (1024**2)
                    compression_ratio = (
                        1.0
                        if codec == "no_compression"
                        else read_write_zarr.get_compression_ratio(store_path)
                    )

                    results_for_run.append(
                        {
                            "write_time": write_time,
                            "read_time": read_time,
                            "size_mb": size_mb,
                            "compression_ratio": compression_ratio,
                        }
                    )

                    # Cleanup
                    utils.remove_output_dir(store_path)

                # Aggregate results
                avg_results = {
                    "codec": codec,
                    "chunks": str(chunks),
                    "write_time_avg": np.mean(
                        [r["write_time"] for r in results_for_run]
                    ),
                    "write_time_std": np.std(
                        [r["write_time"] for r in results_for_run]
                    ),
                    "read_time_avg": np.mean([r["read_time"] for r in results_for_run]),
                    "read_time_std": np.std([r["read_time"] for r in results_for_run]),
                    "size_mb": results_for_run[0]["size_mb"],
                    "compression_ratio": results_for_run[0]["compression_ratio"],
                    "throughput_write_mbs": self.config.dataset_metadata.total_size_mb
                    / np.mean([r["write_time"] for r in results_for_run]),
                    "throughput_read_mbs": self.config.dataset_metadata.total_size_mb
                    / np.mean([r["read_time"] for r in results_for_run]),
                }

                all_results.append(avg_results)
                print(
                    f"    {chunks}: W:{avg_results['write_time_avg']:.3f}s "
                    f"R:{avg_results['read_time_avg']:.3f}s "
                    f"Ratio:{avg_results['compression_ratio']:.2f}×"
                )

        # Save results
        if self.config.save_results:
            df = pd.DataFrame(all_results)
            csv_path = output_dir / "benchmark_results.csv"
            df.to_csv(csv_path, index=False)
            print(f"\n  ✓ Results saved to: {csv_path}")

        # Find best codec
        df = pd.DataFrame(all_results)
        best_write = df.loc[df["write_time_avg"].idxmin()]
        best_read = df.loc[df["read_time_avg"].idxmin()]
        best_compression = df.loc[df["compression_ratio"].idxmax()]

        summary = {
            "dataset": self.config.dataset_metadata.name,
            "dataset_type": self.config.dataset_metadata.dataset_type.value,
            "shape": list(self.config.dataset_metadata.shape),
            "size_mb": self.config.dataset_metadata.total_size_mb,
            "best_write": {
                "codec": best_write["codec"],
                "time_s": best_write["write_time_avg"],
                "throughput_mbs": best_write["throughput_write_mbs"],
            },
            "best_read": {
                "codec": best_read["codec"],
                "time_s": best_read["read_time_avg"],
                "throughput_mbs": best_read["throughput_read_mbs"],
            },
            "best_compression": {
                "codec": best_compression["codec"],
                "ratio": best_compression["compression_ratio"],
                "size_mb": best_compression["size_mb"],
            },
            "all_results": all_results,
        }

        self.results = all_results
        return summary


def run_multi_dataset_benchmark() -> Dict[str, Any]:
    """Run benchmarks across multiple dataset types"""

    print("\nGenerating test datasets...")

    # Define test datasets
    datasets = []

    # 1. CryoET (small)
    print("  - CryoET dataset (128³)")
    cryoet_data = generate_synthetic_volume(128, pattern="realistic", seed=42)
    cryoet_config = BenchmarkConfig(
        dataset_metadata=create_cryoet_metadata((128, 128, 128), source="synthetic"),
        compression_profile=CompressionProfile.BALANCED,
        codecs_to_test=["blosc_zstd", "blosc_lz4", "gzip"],
        num_runs=2,
        output_dir="data/output/multi_dataset_benchmark",
    )
    datasets.append(("cryoet", cryoet_data, cryoet_config))

    # 2. Light sheet (4D: T=5, Z=50, Y=256, X=256)
    print("  - Light sheet dataset (5×50×256×256)")
    lightsheet_data = np.random.randint(0, 65535, (5, 50, 256, 256), dtype=np.uint16)
    lightsheet_config = BenchmarkConfig(
        dataset_metadata=create_lightsheet_metadata(
            (5, 50, 256, 256), voxel_size=(2.0, 0.4, 0.4), source="synthetic"
        ),
        compression_profile=CompressionProfile.FAST,
        codecs_to_test=["blosc_lz4", "blosc_zstd"],
        num_runs=2,
        output_dir="data/output/multi_dataset_benchmark",
    )
    datasets.append(("lightsheet", lightsheet_data, lightsheet_config))

    # 3. Confocal (5D: T=3, C=3, Z=32, Y=512, X=512)
    print("  - Confocal dataset (3×3×32×512×512)")
    confocal_data = np.random.randint(0, 4095, (3, 3, 32, 512, 512), dtype=np.uint16)
    confocal_config = BenchmarkConfig(
        dataset_metadata=create_confocal_metadata(
            (3, 3, 32, 512, 512),
            voxel_size=(0.5, 0.1, 0.1),
            channels=3,
            source="synthetic",
        ),
        compression_profile=CompressionProfile.BALANCED,
        codecs_to_test=["blosc_lz4", "blosc_zstd"],
        num_runs=2,
        output_dir="data/output/multi_dataset_benchmark",
    )
    datasets.append(("confocal", confocal_data, confocal_config))

    print(f"\n✓ Generated {len(datasets)} test datasets")

    # Run benchmarks
    summaries = []
    for dataset_name, data, config in datasets:
        runner = DatasetBenchmarkRunner(config)
        summary = runner.run(data)
        summaries.append(summary)

    # Generate overall report
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_datasets": len(datasets),
        "datasets": summaries,
    }

    # Save overall report
    output_dir = pathlib.Path("data/output/multi_dataset_benchmark")
    report_path = output_dir / "multi_dataset_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n{'=' * 80}")
    print(f"✓ Overall report saved to: {report_path}")
    print(f"{'=' * 80}")

    return report


if __name__ == "__main__":
    start_time = time.time()

    report = run_multi_dataset_benchmark()

    total_time = time.time() - start_time

    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)

    for dataset_summary in report["datasets"]:
        print(f"\n{dataset_summary['dataset']} ({dataset_summary['dataset_type']})")
        print(f"  Size: {dataset_summary['size_mb']:.2f} MB")
        print(f"  Best write: {dataset_summary['best_write']['codec']}")
        print(f"    - Time: {dataset_summary['best_write']['time_s']:.3f}s")
        print(
            f"    - Throughput: {dataset_summary['best_write']['throughput_mbs']:.2f} MB/s"
        )
        print(f"  Best read: {dataset_summary['best_read']['codec']}")
        print(f"    - Time: {dataset_summary['best_read']['time_s']:.3f}s")
        print(
            f"    - Throughput: {dataset_summary['best_read']['throughput_mbs']:.2f} MB/s"
        )
        print(f"  Best compression: {dataset_summary['best_compression']['codec']}")
        print(f"    - Ratio: {dataset_summary['best_compression']['ratio']:.2f}×")
        print(
            f"    - Compressed size: {dataset_summary['best_compression']['size_mb']:.2f} MB"
        )

    print(f"\n{'=' * 80}")
    print(f"Total time: {total_time:.2f}s")
    print(f"{'=' * 80}")
