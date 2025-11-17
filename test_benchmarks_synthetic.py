"""
Fast Benchmark Test Suite with Synthetic Data

Runs all benchmark tests on synthetic data for CI/CD, quick validation,
and demonstrations without requiring CryoET Portal downloads.

Runtime: ~30-60 seconds for full suite
"""

import os
import sys
import time
import pathlib
import numpy as np
import pandas as pd
from test_data_generator import generate_synthetic_volume, get_test_dataset_info
from zarr_benchmarks.read_write_zarr import read_write_zarr
from zarr_benchmarks import utils
from skimage.metrics import structural_similarity as ssim, peak_signal_noise_ratio as psnr
import zarr

# Enable v3 for testing
os.environ["ZARR_V3_EXPERIMENTAL_API"] = "1"


def test_compression_codecs(data: np.ndarray, output_dir: pathlib.Path):
    """Test different compression codecs"""
    print("\n" + "=" * 70)
    print("TEST 1: Compression Codecs")
    print("=" * 70)

    results = []
    codecs = ["blosc_zstd", "blosc_lz4", "blosc_zlib", "zstd", "gzip", "no_compression"]
    level = 5
    chunk_size = 64

    for codec in codecs:
        print(f"\n  Testing {codec}...", end=" ")

        store_path = output_dir / f"compression_test_{codec}.zarr"
        utils.remove_output_dir(store_path)

        try:
            # Setup compressor
            if codec == "no_compression":
                compressor = None
            elif "blosc" in codec:
                cname = codec.split("_")[1]
                compressor = read_write_zarr.get_blosc_compressor(cname, level, "shuffle")
            elif codec == "zstd":
                compressor = read_write_zarr.get_zstd_compressor(level)
            elif codec == "gzip":
                compressor = read_write_zarr.get_gzip_compressor(level)
            else:
                compressor = None

            # Write
            t0 = time.time()
            read_write_zarr.write_zarr_array(
                data,
                store_path,
                overwrite=False,
                chunks=(chunk_size, chunk_size, chunk_size),
                compressor=compressor,
                zarr_spec=2,
            )
            write_time = time.time() - t0

            # Read
            t0 = time.time()
            read_back = read_write_zarr.read_zarr_array(store_path)
            read_time = time.time() - t0

            # Metrics
            size_mb = utils.get_directory_size(store_path) / (1024**2)
            ratio = (
                1.0
                if codec == "no_compression"
                else read_write_zarr.get_compression_ratio(store_path)
            )

            results.append(
                {
                    "codec": codec,
                    "write_time": write_time,
                    "read_time": read_time,
                    "size_mb": size_mb,
                    "ratio": ratio,
                    "success": True,
                }
            )

            print(f"✓ W:{write_time:.3f}s R:{read_time:.3f}s {ratio:.2f}×")

        except Exception as e:
            print(f"✗ {e}")
            results.append({"codec": codec, "success": False, "error": str(e)})

    return pd.DataFrame(results)


def test_zarr_versions(data: np.ndarray, output_dir: pathlib.Path):
    """Test Zarr v2 vs v3"""
    print("\n" + "=" * 70)
    print("TEST 2: Zarr v2 vs v3")
    print("=" * 70)

    # Ensure v3 is enabled
    os.environ["ZARR_V3_EXPERIMENTAL_API"] = "1"

    results = []
    codec = "blosc_zstd"
    level = 5
    chunk_size = 64

    for version in [2, 3]:
        print(f"\n  Testing v{version}...", end=" ")

        store_path = output_dir / f"version_test_v{version}.zarr"
        utils.remove_output_dir(store_path)

        try:
            compressor = read_write_zarr.get_blosc_compressor("zstd", level, "shuffle")

            # Write
            t0 = time.time()
            read_write_zarr.write_zarr_array(
                data,
                store_path,
                overwrite=False,
                chunks=(chunk_size, chunk_size, chunk_size),
                compressor=compressor,
                zarr_spec=version,
            )
            write_time = time.time() - t0

            # Read
            t0 = time.time()
            read_back = read_write_zarr.read_zarr_array(store_path)
            read_time = time.time() - t0

            # Metrics
            size_mb = utils.get_directory_size(store_path) / (1024**2)
            ratio = read_write_zarr.get_compression_ratio(store_path)

            # Count files
            file_count = sum(1 for _ in pathlib.Path(store_path).rglob("*") if _.is_file())

            results.append(
                {
                    "version": f"v{version}",
                    "write_time": write_time,
                    "read_time": read_time,
                    "size_mb": size_mb,
                    "ratio": ratio,
                    "file_count": file_count,
                    "success": True,
                }
            )

            print(f"✓ W:{write_time:.3f}s R:{read_time:.3f}s {ratio:.2f}× Files:{file_count}")

        except Exception as e:
            print(f"✗ {e}")
            results.append({"version": f"v{version}", "success": False, "error": str(e)})

    return pd.DataFrame(results)


def test_chunking_strategies(data: np.ndarray, output_dir: pathlib.Path):
    """Test different chunk sizes"""
    print("\n" + "=" * 70)
    print("TEST 3: Chunking Strategies")
    print("=" * 70)

    results = []
    chunk_sizes = [32, 64, 128]
    codec = "blosc_zstd"
    level = 5

    for chunk_size in chunk_sizes:
        print(f"\n  Testing {chunk_size}³...", end=" ")

        store_path = output_dir / f"chunk_test_{chunk_size}.zarr"
        utils.remove_output_dir(store_path)

        try:
            compressor = read_write_zarr.get_blosc_compressor("zstd", level, "shuffle")

            # Write
            t0 = time.time()
            read_write_zarr.write_zarr_array(
                data,
                store_path,
                overwrite=False,
                chunks=(chunk_size, chunk_size, chunk_size),
                compressor=compressor,
                zarr_spec=2,
            )
            write_time = time.time() - t0

            # Read
            t0 = time.time()
            read_back = read_write_zarr.read_zarr_array(store_path)
            read_time = time.time() - t0

            # Metrics
            size_mb = utils.get_directory_size(store_path) / (1024**2)
            file_count = sum(1 for _ in pathlib.Path(store_path).rglob("*") if _.is_file())

            results.append(
                {
                    "chunk_size": f"{chunk_size}³",
                    "write_time": write_time,
                    "read_time": read_time,
                    "size_mb": size_mb,
                    "file_count": file_count,
                    "success": True,
                }
            )

            print(f"✓ W:{write_time:.3f}s R:{read_time:.3f}s Files:{file_count}")

        except Exception as e:
            print(f"✗ {e}")
            results.append({"chunk_size": f"{chunk_size}³", "success": False, "error": str(e)})

    return pd.DataFrame(results)


def test_data_integrity(data: np.ndarray, output_dir: pathlib.Path):
    """Test lossless compression integrity"""
    print("\n" + "=" * 70)
    print("TEST 4: Data Integrity (Comprehensive Metrics)")
    print("=" * 70)

    results = []
    codecs = ["blosc_zstd", "blosc_lz4", "blosc_zlib", "zstd", "gzip"]
    level = 5
    chunk_size = 64

    for codec in codecs:
        print(f"\n  Testing {codec}...", end=" ")

        store_path = output_dir / f"integrity_test_{codec}.zarr"
        utils.remove_output_dir(store_path)

        try:
            if "blosc" in codec:
                cname = codec.split("_")[1]
                compressor = read_write_zarr.get_blosc_compressor(cname, level, "shuffle")
            elif codec == "zstd":
                compressor = read_write_zarr.get_zstd_compressor(level)
            elif codec == "gzip":
                compressor = read_write_zarr.get_gzip_compressor(level)
            else:
                compressor = None

            # Write and read
            read_write_zarr.write_zarr_array(
                data,
                store_path,
                overwrite=False,
                chunks=(chunk_size, chunk_size, chunk_size),
                compressor=compressor,
                zarr_spec=2,
            )
            read_back = read_write_zarr.read_zarr_array(store_path)

            # Calculate metrics
            is_exact = np.array_equal(data, read_back)

            # SSIM on middle slice
            orig_norm = (data - data.min()) / (data.max() - data.min() + 1e-10)
            read_norm = (read_back - read_back.min()) / (read_back.max() - read_back.min() + 1e-10)
            mid = data.shape[0] // 2
            ssim_val = ssim(orig_norm[mid], read_norm[mid], data_range=1.0)

            # PSNR
            data_range = data.max() - data.min()
            psnr_val = psnr(data, read_back, data_range=data_range)

            # Additional metrics
            from skimage.metrics import mean_squared_error as mse_func

            mse_val = mse_func(data, read_back)
            mae_val = np.mean(np.abs(data - read_back))  # Mean Absolute Error
            max_error = np.max(np.abs(data - read_back))
            correlation = np.corrcoef(data.flat, read_back.flat)[0, 1]

            results.append(
                {
                    "codec": codec,
                    "exact_match": is_exact,
                    "ssim": ssim_val,
                    "psnr": psnr_val,
                    "mse": mse_val,
                    "mae": mae_val,
                    "max_error": max_error,
                    "correlation": correlation,
                    "success": True,
                }
            )

            print(
                f"✓ Exact:{is_exact} SSIM:{ssim_val:.6f} PSNR:{psnr_val:.1f}dB MSE:{mse_val:.2e} Corr:{correlation:.6f}"
            )

        except Exception as e:
            print(f"✗ {e}")
            results.append({"codec": codec, "success": False, "error": str(e)})

    return pd.DataFrame(results)


def main():
    """Run full test suite"""
    print("=" * 70)
    print("ZARR BENCHMARKS TEST SUITE - SYNTHETIC DATA")
    print("=" * 70)

    # Setup
    output_dir = pathlib.Path("data/output/test_synthetic")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate test data
    print("\nGenerating synthetic test data...")
    data = generate_synthetic_volume(size=128, pattern="realistic")
    info = get_test_dataset_info("realistic")

    print(f"  Pattern: {info['name']}")
    print(f"  Shape: {data.shape}")
    print(f"  Size: {data.nbytes / (1024**2):.2f} MB")
    print(f"  Description: {info['description']}")

    # Run tests
    start_time = time.time()

    results = {}
    results["compression"] = test_compression_codecs(data, output_dir)
    results["versions"] = test_zarr_versions(data, output_dir)
    results["chunking"] = test_chunking_strategies(data, output_dir)
    results["integrity"] = test_data_integrity(data, output_dir)

    total_time = time.time() - start_time

    # Save results
    for test_name, df in results.items():
        csv_path = output_dir / f"{test_name}_results.csv"
        df.to_csv(csv_path, index=False)
        print(f"\n✓ Saved {test_name} results to {csv_path}")

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUITE SUMMARY")
    print("=" * 70)

    total_tests = sum(len(df) for df in results.values())
    successful = sum((df["success"] == True).sum() for df in results.values())
    failed = total_tests - successful

    print(f"\nTotal runtime: {total_time:.2f}s")
    print(f"Total tests: {total_tests}")
    print(f"Successful: {successful} ({successful/total_tests*100:.1f}%)")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {failed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
