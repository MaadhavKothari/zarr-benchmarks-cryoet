# Zarr Benchmarks - Quick Start Guide

## 🎯 TL;DR

You have **two ways** to run the benchmarks:

### Option 1: Python Script (Easiest - Already Works!)

```bash
cd /Users/mkothari/zarr-benchmarks
source venv/bin/activate
python run_benchmark_demo.py
```

✅ **This already worked successfully!**

### Option 2: Jupyter Notebook (Interactive)

1. Open:
   <http://localhost:8889/lab?token=2de0ecf690d5c4a0e07b20910ef2fe025fae8d8cc393b741>
2. Open `zarr_benchmarks_demo.ipynb`
3. **IMPORTANT**: Change kernel to "Python 3.13 (zarr-benchmarks)"
4. Run the cells

---

## 📊 Benchmark Results (From Your Test Run)

```
                Write Time (s)  Read Time (s)  Compression Ratio  Storage Size (MB)
blosc                    0.080          0.027              1.214             52.716
gzip                     0.212          0.048              1.114             57.470
zstd                     0.026          0.020              1.118             57.261
no_compression           0.016          0.014              1.000             64.001

Best Methods:
   Fastest write: no_compression
   Fastest read: no_compression
   Best compression: blosc (1.21x, 52.7 MB)
   Smallest storage: blosc
```

**Key Findings:**

- **Blosc** gives the best compression (saves ~11 MB vs uncompressed)
- **Zstd** is the best balance (fast + decent compression)
- **No compression** is fastest but uses most space

---

## 🔧 How to Fix the Jupyter Notebook Kernel Issue

### The Problem

The notebook was using Python 3.12 instead of Python 3.13, which causes
`ModuleNotFoundError`.

### The Solution

**Step 1: Make sure Jupyter Lab is running**

```bash
# Check if it's running:
# You should see output showing it's running on port 8889
```

**Step 2: Open the notebook in your browser**

```
http://localhost:8889/lab?token=2de0ecf690d5c4a0e07b20910ef2fe025fae8d8cc393b741
```

**Step 3: Select the correct kernel**

In Jupyter Lab:

1. Open `zarr_benchmarks_demo.ipynb`
2. Look at the top-right corner - you'll see the current kernel name
3. Click on it (or go to menu: `Kernel` → `Change Kernel...`)
4. Select **"Python 3.13 (zarr-benchmarks)"**
5. The first cell will now verify you're using the right environment

**Step 4: Run the cells**

- Click the "Run" button or press `Shift+Enter` for each cell
- All imports should now work!

---

## 📁 File Locations

**Notebooks:**

- `/Users/mkothari/zarr-benchmarks/zarr_benchmarks_demo.ipynb` - General demo
  (FIXED)
- `/Users/mkothari/zarr-benchmarks/cryoet_portal_benchmark.ipynb` - CryoET data
  (needs extra deps)

**Scripts:**

- `/Users/mkothari/zarr-benchmarks/run_benchmark_demo.py` - Standalone demo
  (WORKS!)
- `/Users/mkothari/zarr-benchmarks/test_setup.py` - Quick test

**Results:**

- `/Users/mkothari/zarr-benchmarks/data/output/demo_benchmarks/` - Benchmark
  results
- `/Users/mkothari/zarr-benchmarks/data/output/demo_benchmarks/benchmark_comparison.png` -
  Plot

---

## 🐛 Debugging Tips

### If Jupyter Lab isn't running

```bash
cd /Users/mkothari/zarr-benchmarks
source venv/bin/activate
jupyter lab --no-browser
```

### If you don't see the "Python 3.13 (zarr-benchmarks)" kernel

```bash
cd /Users/mkothari/zarr-benchmarks
source venv/bin/activate
python -m ipykernel install --user --name=zarr-benchmarks --display-name="Python 3.13 (zarr-benchmarks)"
```

Then refresh your browser and check the kernel menu again.

### If imports still fail

1. Verify you're in the right environment:

   ```bash
   source venv/bin/activate
   python -c "import zarr_benchmarks; print('Success!')"
   ```

2. Check the kernel in Jupyter (top-right corner)
3. Try restarting the kernel: `Kernel` → `Restart Kernel`

### Test the environment

```bash
cd /Users/mkothari/zarr-benchmarks
source venv/bin/activate
python test_setup.py
```

This should complete successfully (it already did!)

---

## 🚀 Next Steps

1. **Experiment with parameters** in `run_benchmark_demo.py`:

   - Change `image_size` (128, 256, 512)
   - Change `chunk_size` (32, 64, 128)
   - Try different compression levels

2. **Use your own data**: Replace this line in the script:

   ```python
   sample_image = np.random.rand(256, 256, 256).astype(np.float32)
   ```

   With your actual imaging data:

   ```python
   sample_image = your_data_array
   ```

3. **Try the CryoET portal notebook** (requires additional setup):

   ```bash
   source venv/bin/activate
   pip install cryoet-data-portal s3fs --no-deps
   pip install aiobotocore boto3 fsspec aiohttp
   ```

4. **Run official benchmarks**:

   ```bash
   source venv/bin/activate
   tox -- --benchmark-only --image=dev --rounds=3
   ```

---

## 📊 Understanding the Plots

The benchmark generates 4 plots:

1. **Write Performance**: How long it takes to save data (lower is better)
2. **Read Performance**: How long it takes to load data (lower is better)
3. **Compression Ratio**: How much space is saved (higher is better)
4. **Storage Size**: Actual file size (lower is better)

**Trade-offs:**

- High compression → Slower write/read but less storage
- No compression → Fastest I/O but most storage
- Sweet spot: Usually Blosc or Zstd with mid-level compression

---

## ✅ What's Working

- ✓ Python 3.13 virtual environment
- ✓ All zarr-benchmarks dependencies installed
- ✓ Standalone script works perfectly
- ✓ Jupyter Lab running on port 8889
- ✓ Kernel installed and available
- ✓ Test suite passes
- ✓ Benchmarks complete successfully
- ✓ Plots generate correctly

## ❓ Questions?

Just ask! I'm here to help debug any issues.
