"""
Dataset Type Definitions for Multi-Modal Benchmarking

Supports various imaging modalities with specific metadata and validation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class DatasetType(Enum):
    """Supported dataset types for benchmarking"""

    CRYOET = "cryoet"  # Cryo-electron tomography
    LIGHT_SHEET = "light_sheet"  # Light sheet microscopy
    CONFOCAL = "confocal"  # Confocal microscopy
    TWO_PHOTON = "two_photon"  # Two-photon microscopy
    WIDEFIELD = "widefield"  # Widefield microscopy
    SEM = "sem"  # Scanning electron microscopy
    STED = "sted"  # STED super-resolution
    PALM_STORM = "palm_storm"  # PALM/STORM localization
    SYNTHETIC = "synthetic"  # Synthetic test data
    CUSTOM = "custom"  # User-defined custom data


class CompressionProfile(Enum):
    """Recommended compression profiles for different use cases"""

    ARCHIVAL = "archival"  # Maximum compression, slower
    BALANCED = "balanced"  # Good compression, reasonable speed
    FAST = "fast"  # Light compression, maximum speed
    LOSSLESS = "lossless"  # Guaranteed lossless
    ANALYSIS = "analysis"  # Optimized for analysis workflows


@dataclass
class DatasetMetadata:
    """Metadata describing a dataset"""

    name: str
    dataset_type: DatasetType
    shape: Tuple[int, ...]
    dtype: np.dtype
    voxel_size: Optional[Tuple[float, ...]] = None  # Physical size per voxel
    units: str = "pixels"  # 'nm', 'um', 'mm', etc.
    channels: int = 1
    timepoints: int = 1
    z_slices: Optional[int] = None
    source: str = "unknown"  # Origin of the data
    modality_specific: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and process metadata"""
        if isinstance(self.dataset_type, str):
            self.dataset_type = DatasetType(self.dataset_type)
        if isinstance(self.dtype, str):
            self.dtype = np.dtype(self.dtype)

    @property
    def ndims(self) -> int:
        """Number of dimensions"""
        return len(self.shape)

    @property
    def total_size_bytes(self) -> int:
        """Total size in bytes"""
        return int(np.prod(self.shape) * self.dtype.itemsize)

    @property
    def total_size_mb(self) -> float:
        """Total size in MB"""
        return self.total_size_bytes / (1024**2)

    @property
    def total_size_gb(self) -> float:
        """Total size in GB"""
        return self.total_size_bytes / (1024**3)

    def suggest_chunk_size(
        self,
        target_mb: float = 64.0,
        compression_profile: CompressionProfile = CompressionProfile.BALANCED,
    ) -> Tuple[int, ...]:
        """
        Suggest optimal chunk size based on dataset characteristics

        Args:
            target_mb: Target chunk size in MB
            compression_profile: Compression profile to optimize for
        """
        # Profile-specific adjustments
        profile_multipliers = {
            CompressionProfile.ARCHIVAL: 2.0,  # Larger chunks for better compression
            CompressionProfile.BALANCED: 1.0,  # Standard size
            CompressionProfile.FAST: 0.5,  # Smaller chunks for faster access
            CompressionProfile.LOSSLESS: 1.5,  # Moderate chunks
            CompressionProfile.ANALYSIS: 1.0,  # Analysis-optimized
        }

        target_mb *= profile_multipliers[compression_profile]
        target_bytes = target_mb * 1024 * 1024
        target_elements = int(target_bytes / self.dtype.itemsize)

        # Start with equal division across dimensions
        ndims = len(self.shape)
        chunk_size_1d = int(target_elements ** (1.0 / ndims))

        # Build chunk shape
        chunks = []
        for dim_size in self.shape:
            chunk_dim = min(chunk_size_1d, dim_size)
            # Round to power of 2 for better performance
            chunk_dim = 2 ** int(np.log2(chunk_dim))
            chunk_dim = max(16, min(chunk_dim, 512))  # Clamp to reasonable range
            chunks.append(chunk_dim)

        return tuple(chunks)

    def suggest_compression(self) -> str:
        """Suggest best compression codec based on dataset type"""
        recommendations = {
            DatasetType.CRYOET: "blosc_zstd",  # Good for EM data
            DatasetType.LIGHT_SHEET: "blosc_zstd",  # Large 3D volumes
            DatasetType.CONFOCAL: "blosc_lz4",  # Fast for interactive work
            DatasetType.TWO_PHOTON: "blosc_lz4",  # Similar to confocal
            DatasetType.WIDEFIELD: "blosc_lz4",  # Fast access needed
            DatasetType.SEM: "blosc_zstd",  # High compression for large datasets
            DatasetType.STED: "blosc_zstd",  # Super-resolution, detailed
            DatasetType.PALM_STORM: "blosc_zstd",  # Sparse data
            DatasetType.SYNTHETIC: "blosc_lz4",  # Fast for testing
            DatasetType.CUSTOM: "blosc_zstd",  # Default to best compression
        }
        return recommendations.get(self.dataset_type, "blosc_zstd")


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark runs"""

    dataset_metadata: DatasetMetadata
    compression_profile: CompressionProfile = CompressionProfile.BALANCED
    codecs_to_test: List[str] = field(
        default_factory=lambda: ["blosc_zstd", "blosc_lz4", "zstd", "gzip"]
    )
    chunk_sizes_to_test: Optional[List[Tuple[int, ...]]] = None
    zarr_versions: List[int] = field(default_factory=lambda: [2])
    num_runs: int = 3  # Number of times to run each benchmark
    calculate_metrics: bool = True  # Calculate quality metrics
    output_dir: str = "data/output/benchmarks"
    save_results: bool = True
    webhook_url: Optional[str] = None  # For pipeline integration

    def __post_init__(self):
        """Generate default chunk sizes if not provided"""
        if self.chunk_sizes_to_test is None:
            # Test 3 different chunk sizes
            base_chunks = self.dataset_metadata.suggest_chunk_size(
                compression_profile=self.compression_profile
            )
            self.chunk_sizes_to_test = [
                tuple(c // 2 for c in base_chunks),  # Smaller
                base_chunks,  # Recommended
                tuple(
                    min(c * 2, s)
                    for c, s in zip(base_chunks, self.dataset_metadata.shape)
                ),  # Larger
            ]


def create_cryoet_metadata(
    shape: Tuple[int, int, int], voxel_spacing: float = 13.48, source: str = "unknown"
) -> DatasetMetadata:
    """Helper to create CryoET dataset metadata"""
    return DatasetMetadata(
        name=f"cryoet_{shape[0]}x{shape[1]}x{shape[2]}",
        dataset_type=DatasetType.CRYOET,
        shape=shape,
        dtype=np.dtype(np.float32),
        voxel_size=(voxel_spacing, voxel_spacing, voxel_spacing),
        units="angstrom",
        z_slices=shape[0],
        source=source,
        modality_specific={
            "electron_dose": "unknown",
            "defocus": "unknown",
            "tilt_range": "unknown",
        },
    )


def create_lightsheet_metadata(
    shape: Tuple[int, int, int, int],  # TZYX
    voxel_size: Tuple[float, float, float] = (2.0, 0.4, 0.4),
    source: str = "unknown",
) -> DatasetMetadata:
    """Helper to create light sheet microscopy metadata"""
    return DatasetMetadata(
        name=f"lightsheet_{shape[1]}z_{shape[2]}x{shape[3]}y",
        dataset_type=DatasetType.LIGHT_SHEET,
        shape=shape,
        dtype=np.dtype(np.uint16),
        voxel_size=voxel_size,
        units="um",
        timepoints=shape[0],
        z_slices=shape[1],
        source=source,
        modality_specific={
            "illumination": "single_side",
            "objective_na": 1.0,
            "wavelength": 488,
        },
    )


def create_confocal_metadata(
    shape: Tuple[int, int, int, int, int],  # TCZYX
    voxel_size: Tuple[float, float, float] = (0.5, 0.1, 0.1),
    channels: int = 3,
    source: str = "unknown",
) -> DatasetMetadata:
    """Helper to create confocal microscopy metadata"""
    return DatasetMetadata(
        name=f"confocal_{channels}ch_{shape[2]}z",
        dataset_type=DatasetType.CONFOCAL,
        shape=shape,
        dtype=np.dtype(np.uint16),
        voxel_size=voxel_size,
        units="um",
        channels=channels,
        timepoints=shape[0],
        z_slices=shape[2],
        source=source,
        modality_specific={
            "pinhole_size": 1.0,
            "objective_na": 1.4,
            "immersion": "oil",
        },
    )
