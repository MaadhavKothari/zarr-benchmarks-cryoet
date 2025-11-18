#!/usr/bin/env python3
"""
Webhook Server for Zarr Benchmark Pipeline Integration

Receives webhook requests from imaging pipelines, runs benchmarks, and reports results.
Supports asynchronous processing with job queuing.
"""

import asyncio
import json
import logging
import pathlib
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

import numpy as np
from aiohttp import web

from zarr_benchmarks.dataset_types import (
    BenchmarkConfig,
    DatasetMetadata,
    DatasetType,
    CompressionProfile,
    create_cryoet_metadata,
    create_lightsheet_metadata,
    create_confocal_metadata,
)
from test_data_generator import generate_synthetic_volume
from multi_dataset_benchmark import DatasetBenchmarkRunner

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Status of benchmark jobs"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BenchmarkJob:
    """Represents a benchmark job"""

    def __init__(self, job_id: str, config: Dict[str, Any], callback_url: Optional[str] = None):
        self.job_id = job_id
        self.config = config
        self.callback_url = callback_url
        self.status = JobStatus.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.results: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary"""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "results": self.results,
            "error": self.error,
        }


class BenchmarkWebhookServer:
    """Webhook server for benchmark integration"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.jobs: Dict[str, BenchmarkJob] = {}
        self.job_queue: asyncio.Queue = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the webhook server"""
        app = web.Application()
        app.router.add_post("/webhook/benchmark", self.handle_benchmark_request)
        app.router.add_get("/status/{job_id}", self.handle_status_request)
        app.router.add_get("/health", self.handle_health_check)
        app.router.add_get("/", self.handle_root)

        # Start background worker
        self.worker_task = asyncio.create_task(self.process_jobs())

        logger.info(f"Starting webhook server on {self.host}:{self.port}")
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        logger.info("Webhook server started successfully")
        logger.info(f"  - Benchmark endpoint: http://{self.host}:{self.port}/webhook/benchmark")
        logger.info(f"  - Status endpoint: http://{self.host}:{self.port}/status/{{job_id}}")
        logger.info(f"  - Health check: http://{self.host}:{self.port}/health")

        # Keep server running
        await asyncio.Event().wait()

    async def handle_root(self, request: web.Request) -> web.Response:
        """Handle root endpoint"""
        return web.json_response(
            {
                "service": "Zarr Benchmark Webhook Server",
                "version": "1.0.0",
                "endpoints": {
                    "benchmark": "/webhook/benchmark (POST)",
                    "status": "/status/{job_id} (GET)",
                    "health": "/health (GET)",
                },
            }
        )

    async def handle_health_check(self, request: web.Request) -> web.Response:
        """Handle health check requests"""
        return web.json_response(
            {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "jobs": {
                    "total": len(self.jobs),
                    "pending": sum(1 for j in self.jobs.values() if j.status == JobStatus.PENDING),
                    "running": sum(1 for j in self.jobs.values() if j.status == JobStatus.RUNNING),
                    "completed": sum(
                        1 for j in self.jobs.values() if j.status == JobStatus.COMPLETED
                    ),
                    "failed": sum(1 for j in self.jobs.values() if j.status == JobStatus.FAILED),
                },
            }
        )

    async def handle_benchmark_request(self, request: web.Request) -> web.Response:
        """Handle incoming benchmark webhook requests"""
        try:
            data = await request.json()
            logger.info(f"Received benchmark request: {json.dumps(data, indent=2)}")

            # Validate request
            if "dataset" not in data:
                return web.json_response(
                    {"error": "Missing 'dataset' field in request"}, status=400
                )

            # Create job
            job_id = str(uuid.uuid4())
            callback_url = data.get("callback_url")
            job = BenchmarkJob(job_id=job_id, config=data, callback_url=callback_url)
            self.jobs[job_id] = job

            # Add to queue
            await self.job_queue.put(job)

            logger.info(f"Created benchmark job: {job_id}")

            return web.json_response(
                {
                    "job_id": job_id,
                    "status": "accepted",
                    "message": "Benchmark job created and queued",
                    "status_url": f"/status/{job_id}",
                },
                status=202,
            )

        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON in request body"}, status=400)
        except Exception as e:
            logger.error(f"Error handling benchmark request: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_status_request(self, request: web.Request) -> web.Response:
        """Handle job status requests"""
        job_id = request.match_info["job_id"]

        if job_id not in self.jobs:
            return web.json_response({"error": "Job not found"}, status=404)

        job = self.jobs[job_id]
        return web.json_response(job.to_dict())

    async def process_jobs(self):
        """Background worker to process benchmark jobs"""
        logger.info("Starting job processing worker")

        while True:
            try:
                # Get next job from queue
                job = await self.job_queue.get()
                logger.info(f"Processing job: {job.job_id}")

                job.status = JobStatus.RUNNING
                job.started_at = datetime.now()

                try:
                    # Run benchmark
                    results = await self.run_benchmark(job.config)
                    job.results = results
                    job.status = JobStatus.COMPLETED
                    logger.info(f"Job {job.job_id} completed successfully")

                    # Send callback if URL provided
                    if job.callback_url:
                        await self.send_callback(job)

                except Exception as e:
                    logger.error(f"Job {job.job_id} failed: {e}")
                    job.status = JobStatus.FAILED
                    job.error = str(e)

                job.completed_at = datetime.now()
                self.job_queue.task_done()

            except Exception as e:
                logger.error(f"Error in job processing worker: {e}")
                await asyncio.sleep(1)

    async def run_benchmark(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run benchmark based on configuration

        Expected config format:
        {
            "dataset": {
                "name": "example",
                "type": "cryoet",
                "shape": [100, 512, 512],
                "dtype": "float32",
                "voxel_size": [13.48, 13.48, 13.48],
                "data_url": "s3://bucket/data.zarr" or "file:///path/to/data" (optional for synthetic)
            },
            "benchmark": {
                "codecs": ["blosc_zstd", "blosc_lz4"],
                "chunk_sizes": [[64, 64, 64]],
                "compression_profile": "balanced",
                "num_runs": 2
            }
        }
        """
        logger.info("Running benchmark...")

        # Parse config
        dataset_config = config["dataset"]
        benchmark_config = config.get("benchmark", {})

        # Create metadata based on dataset type
        dataset_type = dataset_config.get("type", "custom")
        shape = tuple(dataset_config["shape"])

        if dataset_type == "cryoet":
            voxel_spacing = (
                dataset_config.get("voxel_size", [13.48])[0]
                if "voxel_size" in dataset_config
                else 13.48
            )
            metadata = create_cryoet_metadata(shape, voxel_spacing, source="webhook")
        elif dataset_type == "light_sheet":
            voxel_size = tuple(
                dataset_config.get("voxel_size", [2.0, 0.4, 0.4])[:3]
            )  # ZYX order
            metadata = create_lightsheet_metadata(shape, voxel_size, source="webhook")
        elif dataset_type == "confocal":
            voxel_size = tuple(
                dataset_config.get("voxel_size", [0.5, 0.1, 0.1])[:3]
            )  # ZYX order
            channels = dataset_config.get("channels", 3)
            metadata = create_confocal_metadata(shape, voxel_size, channels, source="webhook")
        else:
            # Generic custom dataset
            metadata = DatasetMetadata(
                name=dataset_config.get("name", "unnamed"),
                dataset_type=DatasetType(dataset_type),
                shape=shape,
                dtype=np.dtype(dataset_config.get("dtype", "float32")),
                voxel_size=tuple(dataset_config["voxel_size"])
                if "voxel_size" in dataset_config
                else None,
                source=dataset_config.get("data_url", "webhook"),
            )

        # Generate or load data
        # For now, generate synthetic data (in production, would load from data_url)
        logger.info(f"Generating synthetic data for {metadata.dataset_type.value} dataset...")
        if dataset_type == "cryoet":
            data = generate_synthetic_volume(shape[0], pattern="realistic", seed=42)
        else:
            # Generate appropriate data type for the modality
            if metadata.dtype == np.float32:
                data = np.random.randn(*shape).astype(np.float32)
            else:
                data = np.random.randint(0, 4095, shape, dtype=np.uint16)

        # Create benchmark configuration
        compression_profile_str = benchmark_config.get("compression_profile", "balanced")
        compression_profile = CompressionProfile(compression_profile_str)

        codecs_to_test = benchmark_config.get("codecs", ["blosc_zstd", "blosc_lz4"])
        chunk_sizes = benchmark_config.get("chunk_sizes")
        if chunk_sizes:
            chunk_sizes = [tuple(cs) for cs in chunk_sizes]

        num_runs = benchmark_config.get("num_runs", 2)

        bench_config = BenchmarkConfig(
            dataset_metadata=metadata,
            compression_profile=compression_profile,
            codecs_to_test=codecs_to_test,
            chunk_sizes_to_test=chunk_sizes,
            num_runs=num_runs,
            output_dir="data/output/webhook_benchmarks",
            save_results=True,
        )

        # Run benchmark in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        runner = DatasetBenchmarkRunner(bench_config)

        logger.info("Starting benchmark execution...")
        summary = await loop.run_in_executor(None, runner.run, data)

        logger.info("Benchmark completed successfully")
        return summary

    async def send_callback(self, job: BenchmarkJob):
        """Send results to callback URL"""
        if not job.callback_url:
            return

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    job.callback_url, json=job.to_dict(), timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Callback sent successfully for job {job.job_id}")
                    else:
                        logger.warning(
                            f"Callback failed for job {job.job_id}: HTTP {response.status}"
                        )
        except Exception as e:
            logger.error(f"Error sending callback for job {job.job_id}: {e}")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Zarr Benchmark Webhook Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    args = parser.parse_args()

    server = BenchmarkWebhookServer(host=args.host, port=args.port)
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
