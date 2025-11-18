"""
Synthetic Test Data Generator for Zarr Benchmarking

Generates various types of synthetic 3D volumes for testing benchmarking pipelines
without requiring large downloads or specific datasets.
"""

from typing import Literal

import numpy as np


def generate_synthetic_volume(
    size: int = 256,
    dtype: np.dtype = np.float32,
    pattern: Literal["noise", "gradient", "spheres", "realistic"] = "realistic",
    seed: int = 42,
) -> np.ndarray:
    """
    Generate synthetic 3D volume for testing.

    Parameters
    ----------
    size : int
        Cube dimension (creates size³ volume)
    dtype : np.dtype
        Data type for array
    pattern : str
        Type of pattern to generate:
        - 'noise': Random Gaussian noise
        - 'gradient': Smooth gradient
        - 'spheres': Multiple spheres with varying intensity
        - 'realistic': Simulated microscopy-like data
    seed : int
        Random seed for reproducibility

    Returns
    -------
    np.ndarray
        3D volume of shape (size, size, size)
    """
    np.random.seed(seed)

    if pattern == "noise":
        # Pure Gaussian noise
        data = np.random.randn(size, size, size).astype(dtype)

    elif pattern == "gradient":
        # Smooth 3D gradient
        z, y, x = np.mgrid[0:size, 0:size, 0:size]
        data = (z + y + x).astype(dtype) / (3 * size)

    elif pattern == "spheres":
        # Multiple spheres with different intensities
        data = np.zeros((size, size, size), dtype=dtype)
        z, y, x = np.mgrid[0:size, 0:size, 0:size]

        # Create 5 random spheres
        for i in range(5):
            center_z = np.random.randint(size // 4, 3 * size // 4)
            center_y = np.random.randint(size // 4, 3 * size // 4)
            center_x = np.random.randint(size // 4, 3 * size // 4)
            radius = np.random.randint(size // 8, size // 4)
            intensity = np.random.rand() * 10

            dist = np.sqrt(
                (z - center_z) ** 2 + (y - center_y) ** 2 + (x - center_x) ** 2
            )
            sphere = intensity * np.exp(-(dist**2) / (2 * (radius / 2) ** 2))
            data += sphere

    elif pattern == "realistic":
        # Simulate realistic microscopy data
        # Base noise
        data = np.random.randn(size, size, size).astype(dtype) * 0.1

        # Add structures (spheres + elongated features)
        z, y, x = np.mgrid[0:size, 0:size, 0:size]

        # Spherical structures
        for i in range(8):
            center_z = np.random.randint(size // 4, 3 * size // 4)
            center_y = np.random.randint(size // 4, 3 * size // 4)
            center_x = np.random.randint(size // 4, 3 * size // 4)
            radius = np.random.randint(size // 12, size // 6)
            intensity = np.random.rand() * 2 + 1

            dist = np.sqrt(
                (z - center_z) ** 2 + (y - center_y) ** 2 + (x - center_x) ** 2
            )
            sphere = intensity * np.exp(-(dist**2) / (2 * (radius / 2) ** 2))
            data += sphere

        # Elongated features (filaments)
        for i in range(3):
            start_z = np.random.randint(0, size)
            start_y = np.random.randint(0, size)
            start_x = np.random.randint(0, size)

            direction = np.random.randn(3)
            direction = direction / np.linalg.norm(direction)

            length = np.random.randint(size // 4, size // 2)
            thickness = np.random.randint(size // 20, size // 10)
            intensity = np.random.rand() * 1.5 + 0.5

            for t in range(length):
                pt_z = int(start_z + direction[0] * t) % size
                pt_y = int(start_y + direction[1] * t) % size
                pt_x = int(start_x + direction[2] * t) % size

                # Add thickness
                for dz in range(-thickness, thickness + 1):
                    for dy in range(-thickness, thickness + 1):
                        for dx in range(-thickness, thickness + 1):
                            if np.sqrt(dz**2 + dy**2 + dx**2) <= thickness:
                                iz = (pt_z + dz) % size
                                iy = (pt_y + dy) % size
                                ix = (pt_x + dx) % size
                                data[iz, iy, ix] += intensity

        # Add smooth background variation
        z_low, y_low, x_low = np.mgrid[
            0 : size : size // 4, 0 : size : size // 4, 0 : size : size // 4
        ]
        background = np.random.randn(size // 4, size // 4, size // 4) * 0.5

        from scipy.ndimage import zoom

        background_full = zoom(background, 4, order=3)[:size, :size, :size]
        data += background_full

    else:
        raise ValueError(f"Unknown pattern: {pattern}")

    # Normalize to reasonable range
    data = (data - data.mean()) / (data.std() + 1e-10)

    return data


def get_test_dataset_info(pattern: str = "realistic") -> dict:
    """
    Get description and properties of test dataset.

    Parameters
    ----------
    pattern : str
        Pattern type

    Returns
    -------
    dict
        Dataset metadata and description
    """
    descriptions = {
        "noise": {
            "name": "Gaussian Noise",
            "description": "Pure random Gaussian noise - tests high entropy data",
            "compressibility": "Poor (high entropy)",
            "use_case": "Worst-case compression testing",
        },
        "gradient": {
            "name": "Smooth Gradient",
            "description": "Smooth 3D gradient - tests low entropy data",
            "compressibility": "Excellent (low entropy)",
            "use_case": "Best-case compression testing",
        },
        "spheres": {
            "name": "Multiple Spheres",
            "description": "Random spheres with varying intensity",
            "compressibility": "Good (structured data)",
            "use_case": "Segmentation-like data testing",
        },
        "realistic": {
            "name": "Realistic Microscopy",
            "description": "Simulated microscopy with structures, filaments, and noise",
            "compressibility": "Moderate (similar to real data)",
            "use_case": "Realistic benchmarking",
        },
    }

    return descriptions.get(pattern, {})


if __name__ == "__main__":
    # Test generation
    print("Testing synthetic data generation...")

    for pattern in ["noise", "gradient", "spheres", "realistic"]:
        print(f"\n{pattern.upper()}:")
        data = generate_synthetic_volume(size=128, pattern=pattern)
        info = get_test_dataset_info(pattern)

        print(f"  Name: {info.get('name', 'N/A')}")
        print(f"  Shape: {data.shape}")
        print(f"  Dtype: {data.dtype}")
        print(f"  Range: [{data.min():.3f}, {data.max():.3f}]")
        print(f"  Mean: {data.mean():.3f} ± {data.std():.3f}")
        print(f"  Description: {info.get('description', 'N/A')}")
        print(f"  Compressibility: {info.get('compressibility', 'N/A')}")

    print("\n✓ All patterns generated successfully")
