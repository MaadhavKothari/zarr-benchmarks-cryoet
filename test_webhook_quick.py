#!/usr/bin/env python3
"""Quick test of webhook server with a small benchmark"""

import asyncio
import json

import aiohttp


async def test_small_benchmark():
    """Test with a very small dataset for quick validation"""
    print("Testing webhook server with small CryoET dataset (32³)...")

    config = {
        "dataset": {
            "name": "cryoet_tiny_test",
            "type": "cryoet",
            "shape": [32, 32, 32],  # Very small for fast testing
            "dtype": "float32",
            "voxel_size": [13.48, 13.48, 13.48],
        },
        "benchmark": {
            "codecs": ["blosc_zstd", "blosc_lz4"],
            "compression_profile": "balanced",
            "num_runs": 1,  # Just 1 run for speed
        },
    }

    async with aiohttp.ClientSession() as session:
        # Submit job
        print("\n→ Submitting benchmark job...")
        async with session.post("http://127.0.0.1:8080/webhook/benchmark", json=config) as resp:
            if resp.status != 202:
                print(f"❌ Error: Status {resp.status}")
                print(await resp.text())
                return

            job_info = await resp.json()
            job_id = job_info["job_id"]
            print(f"✓ Job submitted: {job_id}")

        # Poll for completion
        print("\n→ Polling for completion...")
        max_polls = 60  # 2 minutes max
        poll_count = 0

        while poll_count < max_polls:
            await asyncio.sleep(2)
            poll_count += 1

            async with session.get(f"http://127.0.0.1:8080/status/{job_id}") as resp:
                status = await resp.json()

                if status["status"] == "completed":
                    print(f"✓ Job completed! (after {poll_count * 2}s)")

                    # Display results
                    results = status["results"]
                    dataset = results["dataset"]
                    print(f"\n{'='*60}")
                    print("RESULTS")
                    print(f"{'='*60}")
                    print(f"Dataset: {dataset['dataset']}")
                    print(f"Type: {dataset['dataset_type']}")
                    print(f"Size: {dataset['size_mb']:.2f} MB")

                    print("\nBest Performance:")
                    print(f"  Write: {dataset['best_write']['codec']}")
                    print(f"    Time: {dataset['best_write']['time_s']:.3f}s")
                    print(f"  Read: {dataset['best_read']['codec']}")
                    print(f"    Time: {dataset['best_read']['time_s']:.3f}s")
                    print(f"  Compression: {dataset['best_compression']['codec']}")
                    print(f"    Ratio: {dataset['best_compression']['ratio']:.2f}×")
                    print(f"{'='*60}")
                    return True

                elif status["status"] == "failed":
                    print(f"❌ Job failed: {status.get('error', 'Unknown error')}")
                    return False

                elif status["status"] == "running":
                    print(f"  Still running... ({poll_count * 2}s elapsed)")
                elif status["status"] == "pending":
                    print(f"  Pending... ({poll_count * 2}s elapsed)")

        print(f"⏱️ Timeout after {max_polls * 2}s")
        return False


async def main():
    try:
        # Test health first
        async with aiohttp.ClientSession() as session:
            async with session.get("http://127.0.0.1:8080/health") as resp:
                health = await resp.json()
                print(f"Server Status: {health['status']}")
                print(f"Jobs: {health['jobs']}")

        # Run test
        success = await test_small_benchmark()

        if success:
            print("\n✓ Webhook server test PASSED")
        else:
            print("\n❌ Webhook server test FAILED")

    except aiohttp.ClientConnectorError:
        print("❌ Could not connect to server at http://127.0.0.1:8080")
        print("Make sure the server is running:")
        print("  python benchmark_webhook_server.py")


if __name__ == "__main__":
    asyncio.run(main())
