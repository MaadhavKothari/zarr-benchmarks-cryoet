# Contributing to Zarr-Benchmarks CryoET Extension

Thank you for your interest in contributing! This document provides guidelines for contributing to the CryoET extension of the zarr-benchmarks project.

---

## 🎯 Ways to Contribute

### 1. Testing on New Datasets
- Try benchmarks on different CryoET datasets
- Test on other scientific imaging data (MRI, light sheet, etc.)
- Report results and any issues

### 2. Adding New Benchmarks
- Implement lossy compression tests (ZFP, SZ3)
- Add network performance tests
- Benchmark different storage backends

### 3. Improving Documentation
- Fix typos or unclear explanations
- Add examples or tutorials
- Translate documentation

### 4. Code Improvements
- Optimize benchmark performance
- Add error handling
- Improve code quality

### 5. Zarr v3 Integration
- Test sharding when ecosystem is ready
- Compare v2 vs v3 performance
- Update scripts for v3 API

---

## 🚀 Getting Started

### Prerequisites
```bash
# Python 3.13 recommended
python --version  # Should be 3.13.x

# Git
git --version
```

### Setup Development Environment
```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/zarr-benchmarks.git
cd zarr-benchmarks

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[plots,zarr-python-v3]"
pip install cryoet-data-portal s3fs scikit-image

# Install development tools
pip install pytest black ruff mypy pre-commit

# Setup pre-commit hooks
pre-commit install
```

### Verify Installation
```bash
# Run quick test
python test_cryoet_connection_v2.py

# Should see CryoET portal connection success
```

---

## 📋 Contribution Workflow

### 1. Create an Issue
Before starting work, create an issue describing:
- What you plan to add/fix
- Why it's needed
- How you'll implement it

**Wait for feedback** before investing significant time.

### 2. Create a Branch
```bash
# Update main
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/descriptive-name
# or
git checkout -b fix/issue-number-description
```

### 3. Make Changes
- Follow code style guidelines (see below)
- Add tests if applicable
- Update documentation
- Keep commits atomic and well-described

### 4. Test Your Changes
```bash
# Run quick benchmark
python cryoet_real_data_quick.py

# Run tests if you added any
pytest tests/

# Check code style
black --check .
ruff check .
mypy src/
```

### 5. Commit Changes
```bash
# Stage changes
git add <files>

# Commit with clear message
git commit -m "feat: add ZFP compression benchmark

- Implement ZFP codec integration
- Add quality metrics (SSIM, PSNR)
- Update documentation with results"
```

**Commit Message Format:**
```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions/changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks

### 6. Push and Create PR
```bash
# Push to your fork
git push origin feature/descriptive-name

# Go to GitHub and create Pull Request
# Fill in the PR template
```

---

## 📏 Code Style Guidelines

### Python Style
- **Formatter:** Black (line length 100)
- **Linter:** Ruff
- **Type Checker:** MyPy (optional but encouraged)
- **Docstrings:** Google style

```python
def benchmark_compression(
    data: np.ndarray,
    compressor: Any,
    chunks: tuple[int, int, int]
) -> dict[str, float]:
    """Benchmark a compression configuration.

    Args:
        data: Input 3D array to compress
        compressor: Numcodecs compressor instance
        chunks: Chunk shape (z, y, x)

    Returns:
        Dictionary with benchmark metrics:
            - write_time: Time to write in seconds
            - read_time: Time to read in seconds
            - compression_ratio: Original size / compressed size

    Example:
        >>> from numcodecs import Blosc
        >>> data = np.random.rand(128, 128, 128)
        >>> compressor = Blosc(cname='zstd', clevel=5)
        >>> results = benchmark_compression(data, compressor, (64, 64, 64))
    """
    # Implementation
    pass
```

### File Organization
```python
# Standard library imports
import pathlib
import time
from typing import Any

# Third-party imports
import numpy as np
import zarr
from numcodecs import Blosc

# Local imports
from zarr_benchmarks import utils
from zarr_benchmarks.read_write_zarr import read_write_zarr
```

### Naming Conventions
- **Variables:** `snake_case`
- **Functions:** `snake_case`
- **Classes:** `PascalCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_leading_underscore`

---

## 🧪 Testing Guidelines

### Adding Tests
```python
# tests/test_cryoet_benchmarks.py
import pytest
import numpy as np
from zarr_benchmarks.cryoet import benchmark_compression

def test_benchmark_compression():
    """Test compression benchmark returns expected metrics."""
    data = np.random.rand(64, 64, 64).astype('float32')
    from numcodecs import Blosc
    compressor = Blosc(cname='zstd', clevel=5)

    results = benchmark_compression(data, compressor, (32, 32, 32))

    assert 'write_time' in results
    assert 'read_time' in results
    assert results['write_time'] > 0
    assert results['read_time'] > 0
```

### Running Tests
```bash
# All tests
pytest

# Specific file
pytest tests/test_cryoet_benchmarks.py

# With coverage
pytest --cov=src/zarr_benchmarks --cov-report=html
```

---

## 📖 Documentation Guidelines

### Updating Reports
When adding new benchmarks, update:
1. **README_CRYOET_EXTENSION.md** - Add to quick results
2. **EXECUTIVE_SUMMARY.md** - Update recommendations
3. **TECHNICAL_REPORT.md** - Add detailed analysis
4. **ROADMAP.md** - Mark as completed

### Adding New Documentation
- Use Markdown
- Include code examples
- Add visualizations where helpful
- Link to related docs

### Documentation Structure
```markdown
# Title

**Brief description**

## Overview
[What and why]

## Quick Start
[Minimal example]

## Detailed Guide
[Step by step]

## Results
[Tables, plots]

## Recommendations
[Actionable advice]

## References
[Links]
```

---

## 🎨 Adding Visualizations

### Plot Style
```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 6))
fig.suptitle('Benchmark Results', fontsize=14, fontweight='bold')

# Use these colors for consistency
colors = {
    'blosc_zstd': '#45B7D1',
    'blosc_lz4': '#4ECDC4',
    'zstd': '#95E1D3',
    'no_compression': '#F38181'
}

ax.bar(methods, values, color=colors.values())
ax.set_ylabel('Time (s)')
ax.set_title('Write Performance')
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('output.png', dpi=150, bbox_inches='tight')
```

### Figure Requirements
- **Resolution:** 150 DPI minimum
- **Format:** PNG for web, PDF for papers
- **Size:** <1 MB for README images
- **Alt text:** Always provide descriptions

---

## 🐛 Reporting Issues

### Bug Reports
Use the issue template and include:
1. **Description:** What happened vs what you expected
2. **Environment:**
   ```
   - OS: [e.g., macOS 14.1, Ubuntu 22.04]
   - Python: [e.g., 3.13.0]
   - Zarr: [e.g., 2.18.7]
   ```
3. **Reproduction:** Minimal code to reproduce
4. **Logs:** Error messages and tracebacks
5. **Data:** Sample data if relevant (or description)

### Feature Requests
1. **Use case:** Why is this needed?
2. **Proposal:** How should it work?
3. **Alternatives:** What else did you consider?
4. **Examples:** Show expected usage

---

## 🔍 Code Review Process

### For Contributors
- Respond to feedback promptly
- Be open to suggestions
- Update PR based on reviews
- Mark conversations as resolved when addressed

### Review Checklist
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or justified)
- [ ] Performance impact considered
- [ ] Error handling adequate

---

## 🌟 Contribution Ideas

### Beginner-Friendly
- [ ] Fix typos in documentation
- [ ] Add code comments
- [ ] Improve error messages
- [ ] Add examples to README

### Intermediate
- [ ] Test on new datasets
- [ ] Add visualization improvements
- [ ] Optimize performance
- [ ] Add CLI interface

### Advanced
- [ ] Implement Zarr v3 sharding tests
- [ ] Add lossy compression benchmarks
- [ ] Create web-based tool
- [ ] CI/CD pipeline setup

---

## 📞 Getting Help

### Questions?
- Open a discussion on GitHub
- Ask in Zarr Discourse: https://zarr.discourse.group/
- Check existing issues/PRs

### Stuck?
- Review example scripts
- Check documentation
- Ask for clarification in your PR/issue

---

## 🙏 Recognition

Contributors will be:
- Listed in README acknowledgments
- Mentioned in release notes
- Credited in academic papers (if applicable)

---

## 📜 Code of Conduct

### Our Pledge
We are committed to providing a welcoming and inclusive environment.

### Expected Behavior
- Be respectful and constructive
- Welcome newcomers
- Focus on what's best for the community
- Show empathy

### Unacceptable Behavior
- Harassment or discrimination
- Trolling or insulting comments
- Publishing others' private information
- Other unprofessional conduct

### Enforcement
Violations can be reported to project maintainers. All complaints will be reviewed and investigated.

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

---

## 🎉 Thank You!

Every contribution, no matter how small, is valued and appreciated. Together we can make Zarr benchmarking better for the scientific community!

**Happy contributing! 🚀**
