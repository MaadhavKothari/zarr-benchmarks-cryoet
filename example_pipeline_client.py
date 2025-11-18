#!/usr/bin/env python3
"""
Example Pipeline Integration Client

Demonstrates how to integrate the Zarr benchmark webhook server into an imaging pipeline.
Shows how to submit jobs, poll for status, and retrieve results.
"""

import asyncio
import json
import time
from typing import Any, Dict, Optional

import aiohttp


class BenchmarkClient:
    """Client for interacting with the Zarr benchmark webhook server"""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def health_check(self) -> Dict[str, Any]:
        """Check if the server is healthy"""
        async with self.session.get(f"{self.base_url}/health") as response:
            return await response.json()

    async def submit_benchmark(
        self, config: Dict[str, Any], callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a new benchmark job

        Args:
            config: Benchmark configuration
            callback_url: Optional URL to receive results callback

        Returns:
            Job information including job_id and status_url
        """
        payload = {"dataset": config["dataset"], "benchmark": config.get("benchmark", {})}

        if callback_url:
            payload["callback_url"] = callback_url

        async with self.session.post(
            f"{self.base_url}/webhook/benchmark", json=payload
        ) as response:
            return await response.json()

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get the status of a job"""
        async with self.session.get(f"{self.base_url}/status/{job_id}") as response:
            if response.status == 404:
                raise ValueError(f"Job {job_id} not found")
            return await response.json()

    async def wait_for_completion(
        self, job_id: str, poll_interval: float = 2.0, timeout: float = 300.0
    ) -> Dict[str, Any]:
        """
        Wait for a job to complete, polling at regular intervals

        Args:
            job_id: Job ID to wait for
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait

        Returns:
            Final job status with results

        Raises:
            TimeoutError: If job doesn't complete within timeout
            RuntimeError: If job fails
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = await self.get_job_status(job_id)

            if status["status"] == "completed":
                return status
            elif status["status"] == "failed":
                raise RuntimeError(f"Job failed: {status.get('error', 'Unknown error')}")

            await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")


async def example_cryoet_benchmark():
    """Example: Benchmark a CryoET dataset"""
    print("=" * 80)
    print("Example 1: CryoET Benchmark")
    print("=" * 80)

    config = {
        "dataset": {
            "name": "cryoet_test",
            "type": "cryoet",
            "shape": [128, 128, 128],
            "dtype": "float32",
            "voxel_size": [13.48, 13.48, 13.48],
        },
        "benchmark": {
            "codecs": ["blosc_zstd", "blosc_lz4"],
            "compression_profile": "balanced",
            "num_runs": 2,
        },
    }

    async with BenchmarkClient() as client:
        # Check server health
        health = await client.health_check()
        print(f"\n✓ Server health: {health['status']}")
        print(f"  Jobs: {health['jobs']}")

        # Submit job
        print("\n→ Submitting CryoET benchmark job...")
        job_info = await client.submit_benchmark(config)
        job_id = job_info["job_id"]
        print(f"✓ Job submitted: {job_id}")
        print(f"  Status URL: {job_info['status_url']}")

        # Wait for completion
        print("\n→ Waiting for job to complete...")
        result = await client.wait_for_completion(job_id, poll_interval=2.0)

        # Display results
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)
        print(f"\nJob ID: {result['job_id']}")
        print(f"Status: {result['status']}")
        print(f"Completed at: {result['completed_at']}")

        if result["results"]:
            dataset = result["results"]["dataset"]
            print(f"\nDataset: {dataset['dataset']}")
            print(f"Type: {dataset['dataset_type']}")
            print(f"Size: {dataset['size_mb']:.2f} MB")

            print("\nBest Performance:")
            print(f"  Write: {dataset['best_write']['codec']}")
            print(f"    - Time: {dataset['best_write']['time_s']:.3f}s")
            print(f"    - Throughput: {dataset['best_write']['throughput_mbs']:.2f} MB/s")
            print(f"  Read: {dataset['best_read']['codec']}")
            print(f"    - Time: {dataset['best_read']['time_s']:.3f}s")
            print(f"    - Throughput: {dataset['best_read']['throughput_mbs']:.2f} MB/s")
            print(f"  Compression: {dataset['best_compression']['codec']}")
            print(f"    - Ratio: {dataset['best_compression']['ratio']:.2f}×")
            print(f"    - Size: {dataset['best_compression']['size_mb']:.2f} MB")


async def example_lightsheet_benchmark():
    """Example: Benchmark a light sheet microscopy dataset"""
    print("\n" + "=" * 80)
    print("Example 2: Light Sheet Microscopy Benchmark")
    print("=" * 80)

    config = {
        "dataset": {
            "name": "lightsheet_test",
            "type": "light_sheet",
            "shape": [5, 50, 256, 256],  # T, Z, Y, X
            "dtype": "uint16",
            "voxel_size": [2.0, 0.4, 0.4],  # Z, Y, X in microns
        },
        "benchmark": {
            "codecs": ["blosc_zstd", "blosc_lz4"],
            "compression_profile": "fast",
            "num_runs": 2,
        },
    }

    async with BenchmarkClient() as client:
        print("\n→ Submitting light sheet benchmark job...")
        job_info = await client.submit_benchmark(config)
        job_id = job_info["job_id"]
        print(f"✓ Job submitted: {job_id}")

        print("\n→ Waiting for job to complete...")
        result = await client.wait_for_completion(job_id)

        print("\n✓ Job completed!")
        print(f"  Results available at job ID: {result['job_id']}")


async def example_batch_benchmarks():
    """Example: Submit multiple benchmarks in parallel"""
    print("\n" + "=" * 80)
    print("Example 3: Batch Benchmarks (Multiple Datasets)")
    print("=" * 80)

    configs = [
        {
            "dataset": {
                "name": "cryoet_small",
                "type": "cryoet",
                "shape": [64, 64, 64],
                "dtype": "float32",
            },
            "benchmark": {"codecs": ["blosc_zstd"], "num_runs": 1},
        },
        {
            "dataset": {
                "name": "confocal_test",
                "type": "confocal",
                "shape": [2, 2, 16, 256, 256],  # T, C, Z, Y, X
                "dtype": "uint16",
                "channels": 2,
            },
            "benchmark": {"codecs": ["blosc_lz4"], "num_runs": 1},
        },
    ]

    async with BenchmarkClient() as client:
        print(f"\n→ Submitting {len(configs)} benchmark jobs...")

        # Submit all jobs
        job_ids = []
        for i, config in enumerate(configs):
            job_info = await client.submit_benchmark(config)
            job_ids.append(job_info["job_id"])
            print(f"  ✓ Job {i+1} submitted: {job_info['job_id']}")

        # Wait for all to complete
        print(f"\n→ Waiting for {len(job_ids)} jobs to complete...")
        results = await asyncio.gather(
            *[client.wait_for_completion(job_id) for job_id in job_ids]
        )

        print("\n✓ All jobs completed!")
        for i, result in enumerate(results):
            dataset = result["results"]["dataset"]
            print(f"\n  Job {i+1}: {dataset['dataset']}")
            print(f"    Best codec: {dataset['best_compression']['codec']}")
            print(f"    Compression: {dataset['best_compression']['ratio']:.2f}×")


async def example_with_callback():
    """Example: Submit job with callback URL"""
    print("\n" + "=" * 80)
    print("Example 4: Benchmark with Callback")
    print("=" * 80)
    print("(Requires callback server running on http://localhost:9000/callback)")

    config = {
        "dataset": {
            "name": "cryoet_callback_test",
            "type": "cryoet",
            "shape": [64, 64, 64],
            "dtype": "float32",
        },
        "benchmark": {"codecs": ["blosc_zstd"], "num_runs": 1},
    }

    async with BenchmarkClient() as client:
        print("\n→ Submitting job with callback URL...")
        job_info = await client.submit_benchmark(
            config, callback_url="http://localhost:9000/callback"
        )
        print(f"✓ Job submitted: {job_info['job_id']}")
        print("  Callback will be sent to http://localhost:9000/callback when complete")


async def main():
    """Run all examples"""
    print("\n" + "=" * 80)
    print("ZARR BENCHMARK WEBHOOK CLIENT - EXAMPLES")
    print("=" * 80)
    print("\nMake sure the webhook server is running:")
    print("  python benchmark_webhook_server.py")
    print("\n" + "=" * 80)

    try:
        # Example 1: Single CryoET benchmark
        await example_cryoet_benchmark()

        # Example 2: Light sheet benchmark
        await example_lightsheet_benchmark()

        # Example 3: Batch benchmarks
        await example_batch_benchmarks()

        # Example 4: Callback (optional)
        # await example_with_callback()

        print("\n" + "=" * 80)
        print("✓ All examples completed successfully!")
        print("=" * 80)

    except aiohttp.ClientConnectorError:
        print("\n" + "=" * 80)
        print("ERROR: Could not connect to webhook server")
        print("=" * 80)
        print("\nMake sure the server is running:")
        print("  python benchmark_webhook_server.py")
        print("\nOr specify a different URL:")
        print("  BenchmarkClient(base_url='http://your-server:8080')")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
