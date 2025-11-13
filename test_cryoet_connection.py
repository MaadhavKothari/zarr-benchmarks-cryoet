#!/usr/bin/env python3
"""
Test CryoET Portal API Connection
Quick test to verify we can connect and fetch data
"""

print("=" * 70)
print("Testing CryoET Portal API Connection")
print("=" * 70)

print("\n1. Importing libraries...")
try:
    from cryoet_data_portal import Client, Dataset, Run, Tomogram
    import s3fs
    import zarr
    print("   ✓ All imports successful")
except ImportError as e:
    print(f"   ✗ Import failed: {e}")
    exit(1)

print("\n2. Connecting to CryoET Portal...")
try:
    client = Client()
    print("   ✓ Client created successfully")
except Exception as e:
    print(f"   ✗ Connection failed: {e}")
    exit(1)

print("\n3. Fetching dataset 10445...")
try:
    dataset = Dataset.get_by_id(client, 10445)
    print(f"   ✓ Dataset title: {dataset.title}")
    print(f"   ✓ Dataset ID: {dataset.id}")
except Exception as e:
    print(f"   ✗ Failed to fetch dataset: {e}")
    exit(1)

print("\n4. Getting runs...")
try:
    runs = list(dataset.runs)
    print(f"   ✓ Total runs: {len(runs)}")
    if runs:
        first_run = runs[0]
        print(f"   ✓ First run name: {first_run.name}")
        print(f"   ✓ First run ID: {first_run.id}")
except Exception as e:
    print(f"   ✗ Failed to get runs: {e}")
    exit(1)

print("\n5. Getting tomograms...")
try:
    tomograms = list(first_run.tomograms)
    print(f"   ✓ Tomograms in first run: {len(tomograms)}")
    if tomograms:
        first_tomo = tomograms[0]
        print(f"   ✓ Tomogram name: {first_tomo.name}")
        print(f"   ✓ Size: {first_tomo.size_x} x {first_tomo.size_y} x {first_tomo.size_z}")
        print(f"   ✓ Voxel spacing: {first_tomo.voxel_spacing} Å")
        print(f"   ✓ S3 path: {first_tomo.s3_omezarr_dir}")
except Exception as e:
    print(f"   ✗ Failed to get tomograms: {e}")
    exit(1)

print("\n6. Testing S3 access...")
try:
    s3 = s3fs.S3FileSystem(anon=True)
    zarr_path = first_tomo.s3_omezarr_dir.replace('s3://', '')
    print(f"   ✓ S3 filesystem created")
    print(f"   ✓ Accessing: {zarr_path}")
except Exception as e:
    print(f"   ✗ S3 access failed: {e}")
    exit(1)

print("\n7. Opening zarr array (metadata only)...")
try:
    store = s3fs.S3Map(root=zarr_path, s3=s3, check=False)
    zarr_array = zarr.open(store, mode='r')
    print(f"   ✓ Zarr array opened")
    print(f"   ✓ Shape: {zarr_array.shape}")
    print(f"   ✓ Dtype: {zarr_array.dtype}")
    print(f"   ✓ Chunks: {zarr_array.chunks}")
    print(f"   ✓ Compressor: {zarr_array.compressor}")
    print(f"   ✓ Size: {zarr_array.nbytes / (1024**3):.2f} GB (uncompressed)")
except Exception as e:
    print(f"   ✗ Failed to open zarr: {e}")
    exit(1)

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED!")
print("=" * 70)
print("\nYou can now access real CryoET data from the portal!")
print(f"\nDataset 10445 contains:")
print(f"  - {len(runs)} runs")
print(f"  - {len(tomograms)} tomograms in the first run")
print(f"  - First tomogram: {first_tomo.size_x} x {first_tomo.size_y} x {first_tomo.size_z}")
