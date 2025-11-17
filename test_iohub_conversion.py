"""
Test iohub OME-Zarr Conversion

Quick test of iohub's OME-Zarr capabilities with synthetic data.
Runtime: ~5-10 seconds
"""

import os
import sys
import time
import pathlib
import numpy as np
from test_data_generator import generate_synthetic_volume
from iohub import open_ome_zarr
from zarr_benchmarks import utils
import zarr

# Enable v3
os.environ["ZARR_V3_EXPERIMENTAL_API"] = "1"


def test_iohub_zarr_creation():
    """Test creating OME-Zarr stores with iohub"""
    print("=" * 70)
    print("IOHUB OME-ZARR CONVERSION TEST")
    print("=" * 70)

    # Generate test data
    print("\n1. Generating synthetic data...")
    data = generate_synthetic_volume(size=128, pattern="realistic")
    print(f"   Shape: {data.shape}")
    print(f"   Size: {data.nbytes / (1024**2):.2f} MB")

    output_dir = pathlib.Path("data/output/iohub_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []

    # Test iohub OME-Zarr creation
    print("\n2. Testing iohub OME-Zarr creation...")
    try:
        zarr_v2_path = output_dir / "test_iohub.zarr"
        utils.remove_output_dir(zarr_v2_path)

        t0 = time.time()
        with open_ome_zarr(
            str(zarr_v2_path), layout="hcs", mode="w-", channel_names=["test"]
        ) as dataset:
            # Create position (plate, well, field)
            position = dataset.create_position("A", "1", "0")
            # iohub expects TCZYX format
            data_5d = data[np.newaxis, np.newaxis, ...]  # Add T, C dims
            position["0"] = data_5d

        write_time = time.time() - t0

        # Read back
        t0 = time.time()
        with open_ome_zarr(str(zarr_v2_path), mode="r") as dataset:
            position = dataset["A/1/0"]
            read_data = np.array(position["0"][0, 0, ...])  # Remove T, C
        read_time = time.time() - t0

        # Verify
        is_equal = np.array_equal(data, read_data)
        size_mb = utils.get_directory_size(zarr_v2_path) / (1024**2)

        print(f"   ✓ Write: {write_time:.3f}s, Read: {read_time:.3f}s")
        print(f"   ✓ Size: {size_mb:.2f} MB")
        print(f"   ✓ Data match: {is_equal}")

        results.append(
            {
                "version": "iohub_ome",
                "success": True,
                "write_time": write_time,
                "read_time": read_time,
                "size_mb": size_mb,
                "data_match": is_equal,
            }
        )

    except Exception as e:
        print(f"   ✗ Failed: {e}")
        import traceback

        traceback.print_exc()
        results.append({"version": "iohub_ome", "success": False, "error": str(e)})

    # Test standard zarr for comparison
    print("\n3. Testing standard zarr (comparison)...")
    try:
        from zarr_benchmarks.read_write_zarr import read_write_zarr

        std_zarr_path = output_dir / "test_standard.zarr"
        utils.remove_output_dir(std_zarr_path)

        compressor = read_write_zarr.get_blosc_compressor("zstd", 5, "shuffle")

        t0 = time.time()
        read_write_zarr.write_zarr_array(
            data,
            std_zarr_path,
            overwrite=False,
            chunks=(64, 64, 64),
            compressor=compressor,
            zarr_spec=2,
        )
        write_time = time.time() - t0

        t0 = time.time()
        read_data = read_write_zarr.read_zarr_array(std_zarr_path)
        read_time = time.time() - t0

        is_equal = np.array_equal(data, read_data)
        size_mb = utils.get_directory_size(std_zarr_path) / (1024**2)

        print(f"   ✓ Write: {write_time:.3f}s, Read: {read_time:.3f}s")
        print(f"   ✓ Size: {size_mb:.2f} MB")
        print(f"   ✓ Data match: {is_equal}")

        results.append(
            {
                "version": "standard",
                "success": True,
                "write_time": write_time,
                "read_time": read_time,
                "size_mb": size_mb,
                "data_match": is_equal,
            }
        )

    except Exception as e:
        print(f"   ✗ Failed: {e}")
        results.append({"version": "standard", "success": False, "error": str(e)})

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    successful = sum(1 for r in results if r.get("success", False))
    total = len(results)

    print(f"\nTests: {successful}/{total} successful")

    if successful > 0:
        print("\nComparison:")
        for r in results:
            if r.get("success"):
                print(
                    f"  {r['version']:10s}: Write={r['write_time']:.3f}s "
                    f"Read={r['read_time']:.3f}s Size={r['size_mb']:.2f}MB"
                )

    print("\n💡 Key Findings:")
    print("   • iohub creates OME-NGFF compliant stores (HCS layout)")
    print("   • Adds proper OME-Zarr metadata structure")
    print("   • Uses plate/well/field organization")
    print("   • Standard zarr may be faster for simple arrays")
    print("   • iohub is ideal for high-content screening data")

    return 0 if successful == total else 1


if __name__ == "__main__":
    sys.exit(test_iohub_zarr_creation())
