# 📚 Tutorial: Publishing Zarr-Benchmarks CryoET Extension to GitHub

**Your GitHub:** <https://github.com/MaadhavKothari/> **Repository Name:**
`zarr-benchmarks-cryoet` (suggested) **Visibility:** Public (recommended for
open science)

---

## 🎯 What You're Publishing

A complete benchmarking suite for Zarr storage optimization on real CryoET data,
including:

- 3 production-ready scripts
- 3 Jupyter notebooks
- 8 comprehensive documentation files
- Example outputs and visualizations
- CI/CD pipeline
- Community contribution guidelines

**Impact:** Helps the scientific community optimize data storage, potentially
saving thousands of dollars in cloud costs.

---

## 📋 Prerequisites Checklist

Before starting, make sure you have:

- [ ] GitHub account (yours: <https://github.com/MaadhavKothari/>)
- [ ] Git installed (`git --version`)
- [ ] GitHub CLI installed (optional but recommended): `brew install gh`
- [ ] SSH keys set up with GitHub (or use HTTPS)

---

## 🚀 Step-by-Step Publishing Guide

### Step 1: Initialize Git Repository (if not already done)

```bash
# Navigate to your project
cd /Users/mkothari/zarr-benchmarks

# Check if git is already initialized
git status

# If "not a git repository", initialize it
# (Skip this if already a git repo from HEFTIE fork)
git init
```

**What this does:** Creates a `.git` folder to track your changes.

---

### Step 2: Create .gitignore File

Create `.gitignore` to exclude unnecessary files:

```bash
# Create/update .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environments
venv/
ENV/
env/
venv_v3/
venv_zarr_v3/

# Jupyter Notebook
.ipynb_checkpoints/
*.ipynb_checkpoints/

# macOS
.DS_Store
.AppleDouble
.LSOverride

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Benchmark outputs (optional - you may want to commit small examples)
data/output/*/
!data/output/**/*.png
!data/output/**/*.csv

# Large data files
*.zarr/
*.h5
*.hdf5
*.npy

# Temporary files
*.log
*.tmp
*.bak
EOF
```

**What this does:** Tells Git to ignore temporary files, virtual environments,
and large data files.

---

### Step 3: Stage Your Files

```bash
# Add all documentation files
git add *.md

# Add scripts
git add *.py

# Add notebooks
git add *.ipynb

# Add GitHub workflows
git add .github/

# Add requirements
git add requirements-cryoet.txt

# Add example outputs (small files only)
git add data/output/**/*.png data/output/**/*.csv

# Check what will be committed
git status
```

**What this does:** Prepares your files to be committed.

**Expected output:**

```
Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
        new file:   README_CRYOET_EXTENSION.md
        new file:   CONTRIBUTING.md
        new file:   ROADMAP.md
        ... (and many more)
```

---

### Step 4: Create Initial Commit

```bash
# Create your first commit
git commit -m "feat: add CryoET benchmarking extension

- Real CryoET data integration via Data Portal API
- Compression benchmarks (Blosc-Zstd, LZ4, Zstd, GZip)
- Chunking analysis (16³ to 128³, non-cubic optimizations)
- Comprehensive documentation (8 reports)
- Jupyter notebooks for interactive exploration
- CI/CD pipeline with GitHub Actions
- Example outputs and visualizations

Key findings:
- Blosc-Zstd achieves 1.17× compression (14.4% savings)
- 64³ chunks optimal for general use
- Non-cubic chunks 4× faster for slice viewing
- 99.6% file reduction possible (16³ → 128³)

Built on HEFTIE zarr-benchmarks framework.
Tested on Dataset 10445 from CryoET Data Portal.
"
```

**What this does:** Creates a snapshot of your work with a descriptive message.

---

### Step 5: Create GitHub Repository

#### Option A: Using GitHub CLI (Recommended)

```bash
# Login to GitHub
gh auth login
# Follow prompts, choose HTTPS or SSH

# Create repository
gh repo create zarr-benchmarks-cryoet \
  --public \
  --description "Comprehensive Zarr storage optimization benchmarks for CryoET data - compression, chunking, and sharding analysis" \
  --homepage "https://cryoetdataportal.czscience.com" \
  --source=. \
  --push

# This will:
# 1. Create repo on GitHub
# 2. Set up remote
# 3. Push your code
```

**What this does:** Creates the repository and pushes your code in one command!

#### Option B: Using GitHub Website

1. **Go to:** <https://github.com/new>

2. **Fill in:**

   - Repository name: `zarr-benchmarks-cryoet`
   - Description:
     `Comprehensive Zarr storage optimization benchmarks for CryoET data - compression, chunking, and sharding analysis`
   - Visibility: ☑️ Public
   - DO NOT initialize with README (you already have one)

3. **Click:** "Create repository"

4. **Run these commands:**

   ```bash
   # Add GitHub as remote
   git remote add origin https://github.com/MaadhavKothari/zarr-benchmarks-cryoet.git

   # Push your code
   git branch -M main
   git push -u origin main
   ```

**What this does:** Connects your local repository to GitHub and uploads your
code.

---

### Step 6: Verify Upload

```bash
# Open repository in browser
gh repo view --web
# OR manually visit:
# https://github.com/MaadhavKothari/zarr-benchmarks-cryoet
```

**Check that you see:**

- [ ] README_CRYOET_EXTENSION.md displayed on homepage
- [ ] All documentation files visible
- [ ] Scripts and notebooks present
- [ ] .github/workflows/ directory exists

---

### Step 7: Setup GitHub Pages (for documentation)

#### Enable GitHub Pages

1. **Go to:**
   <https://github.com/MaadhavKothari/zarr-benchmarks-cryoet/settings/pages>

2. **Under "Build and deployment":**

   - Source: Deploy from a branch
   - Branch: `main`
   - Folder: `/ (root)`

3. **Click:** "Save"

4. **Wait ~2 minutes**, then visit:
   - `https://maadhavkothari.github.io/zarr-benchmarks-cryoet/`

Your documentation will be live!

#### Create a nice landing page

```bash
# Create docs/index.html (optional but nice)
mkdir -p docs
cat > docs/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Zarr-Benchmarks CryoET Extension</title>
    <meta http-equiv="refresh" content="0; url=./README_CRYOET_EXTENSION.html">
</head>
<body>
    Redirecting to documentation...
</body>
</html>
EOF

# Commit and push
git add docs/
git commit -m "docs: add GitHub Pages landing page"
git push
```

---

### Step 8: Add Topics/Tags

1. **Go to:** <https://github.com/MaadhavKothari/zarr-benchmarks-cryoet>

2. **Click** the gear icon ⚙️ next to "About"

3. **Add topics:**

   - `zarr`
   - `cryoet`
   - `cryo-electron-microscopy`
   - `benchmarking`
   - `compression`
   - `scientific-computing`
   - `bioimaging`
   - `data-storage`
   - `cloud-optimization`
   - `python`

4. **Add website:** `https://cryoetdataportal.czscience.com`

5. **Click:** "Save changes"

**What this does:** Makes your repository discoverable in GitHub search.

---

### Step 9: Create First Release

```bash
# Create a tag
git tag -a v1.0.0 -m "Release v1.0.0: CryoET benchmarking suite

First public release with comprehensive benchmarks on real CryoET data.

Features:
- Compression analysis (4 codecs)
- Chunking optimization (cubic and non-cubic)
- Real data from CryoET Portal Dataset 10445
- 8 documentation files
- 3 Jupyter notebooks
- CI/CD pipeline

Results:
- Blosc-Zstd: 1.17× compression, 14.4% savings
- 64³ chunks: optimal balance
- 99.6% file reduction possible
"

# Push tag
git push origin v1.0.0
```

**Then on GitHub:**

1. Go to: <https://github.com/MaadhavKothari/zarr-benchmarks-cryoet/releases>
2. Click "Draft a new release"
3. Choose tag: v1.0.0
4. Title: "v1.0.0 - CryoET Benchmarking Suite"
5. Description: Copy from EXECUTIVE_SUMMARY.md key points
6. Click "Publish release"

---

### Step 10: Setup Branch Protection (Optional but Recommended)

1. **Go to:** Settings → Branches → Add branch protection rule

2. **Branch name pattern:** `main`

3. **Enable:**

   - ☑️ Require pull request before merging
   - ☑️ Require status checks to pass (CI tests)
   - ☑️ Require conversation resolution before merging

4. **Click:** "Create"

**What this does:** Protects main branch from accidental direct commits.

---

## 📢 Step 11: Announce Your Work

### On Zarr Discourse

1. **Go to:** <https://zarr.discourse.group/>
2. **Create topic** in "Show and Tell" category
3. **Use template from** `GITHUB_READY_SUMMARY.md`

### On Twitter/X

```
🎉 Excited to share: Comprehensive Zarr storage benchmarks for #CryoET data!

✅ Real tomogram from @cziscience CryoET Portal
✅ 14.4% storage savings with Blosc-Zstd
✅ 99% file reduction with optimal chunking
✅ 4× faster slice viewing

Perfect for data portals & labs with large datasets!

📊 https://github.com/MaadhavKothari/zarr-benchmarks-cryoet

#OpenScience #CryoEM #DataManagement
```

### On LinkedIn

```
I'm pleased to share a comprehensive benchmarking suite for optimizing Zarr storage
in scientific imaging, tested on real cryo-electron tomography data.

Key achievements:
• 14.4% storage cost reduction
• 99% fewer files for cloud storage
• 4× performance improvement for visualization
• Production-ready tools and documentation

This work builds on the excellent HEFTIE project and validates storage optimization
strategies on real scientific data from the CryoET Data Portal.

All code, data, and documentation are open source and ready to use.

Repository: https://github.com/MaadhavKothari/zarr-benchmarks-cryoet

#ScientificComputing #OpenScience #CryoEM #DataManagement
```

---

## 🔄 Ongoing Maintenance

### Regular Updates

```bash
# Make changes
# ...

# Stage changes
git add <files>

# Commit with clear message
git commit -m "fix: improve chunking performance

- Optimize memory usage for large volumes
- Add progress bars
- Fix edge case with non-cubic chunks"

# Push to GitHub
git push
```

### Responding to Issues

When someone opens an issue:

1. Respond within 48 hours
2. Label appropriately (bug, enhancement, question)
3. If it's a good first issue, add that label
4. Be friendly and helpful!

### Accepting Pull Requests

1. Review code changes carefully
2. Run benchmarks to test
3. Ask for changes if needed
4. Merge when satisfied
5. Thank the contributor!

---

## 📊 Track Your Impact

### GitHub Insights

Check regularly:

- **Stars:**
  <https://github.com/MaadhavKothari/zarr-benchmarks-cryoet/stargazers>
- **Forks:**
  <https://github.com/MaadhavKothari/zarr-benchmarks-cryoet/network/members>
- **Traffic:**
  <https://github.com/MaadhavKothari/zarr-benchmarks-cryoet/graphs/traffic>
- **Contributors:**
  <https://github.com/MaadhavKothari/zarr-benchmarks-cryoet/graphs/contributors>

### Citations

Create `CITATION.cff` file:

```bash
cat > CITATION.cff << 'EOF'
cff-version: 1.2.0
title: "Zarr-Benchmarks CryoET Extension"
message: "If you use this software, please cite it as below."
authors:
  - family-names: "Kothari"
    given-names: "Maadhav"
    orcid: "https://orcid.org/YOUR-ORCID"  # Add yours
date-released: 2025-11-12
url: "https://github.com/MaadhavKothari/zarr-benchmarks-cryoet"
repository-code: "https://github.com/MaadhavKothari/zarr-benchmarks-cryoet"
type: software
license: MIT
keywords:
  - zarr
  - cryoet
  - benchmarking
  - compression
  - scientific-computing
EOF

git add CITATION.cff
git commit -m "docs: add citation file"
git push
```

---

## 🎓 Best Practices for Open Source

### Do's ✅

- Respond to issues promptly
- Be welcoming to new contributors
- Keep documentation up to date
- Tag releases regularly
- Thank contributors publicly
- Share your work widely

### Don'ts ❌

- Don't commit large files (>100MB)
- Don't commit API keys or secrets
- Don't force push to main
- Don't ignore security warnings
- Don't be rude to contributors

---

## 🆘 Troubleshooting

### Problem: "Large files" error

```bash
# If git complains about large files:
# Remove them from git history
git rm --cached data/output/large_file.zarr
# Add to .gitignore
echo "*.zarr" >> .gitignore
git commit -m "fix: remove large files from tracking"
```

### Problem: Wrong files committed

```bash
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Remove specific file
git reset HEAD <file>

# Recommit correctly
git commit -m "..."
```

### Problem: Merge conflicts

```bash
# Pull latest changes
git pull origin main

# If conflicts, edit files to resolve
# Then:
git add <resolved-files>
git commit -m "merge: resolve conflicts"
git push
```

---

## 📞 Get Help

- **GitHub Docs:** <https://docs.github.com/>
- **Git Tutorial:** <https://git-scm.com/book/en/v2>
- **GitHub CLI:** <https://cli.github.com/manual/>
- **Zarr Community:** <https://zarr.discourse.group/>

---

## ✅ Post-Publishing Checklist

After publishing, verify:

- [ ] Repository is public
- [ ] README displays correctly
- [ ] All documentation accessible
- [ ] GitHub Pages works
- [ ] CI/CD pipeline runs successfully
- [ ] Issues/discussions enabled
- [ ] Topics/tags added
- [ ] First release created
- [ ] CITATION.cff present
- [ ] Announced on social media

---

## 🎉 Congratulations

Your work is now:

- ✅ Publicly available
- ✅ Professionally documented
- ✅ Ready for collaboration
- ✅ Discoverable by search
- ✅ Citable by others
- ✅ Making an impact!

**You've contributed to open science! 🚀**

---

## 🔮 What's Next?

1. **Monitor** your repository for issues/PRs
2. **Engage** with the community
3. **Iterate** based on feedback
4. **Present** at conferences
5. **Publish** a paper (optional)
6. **Expand** to other domains (MRI, etc.)

**The journey continues!**

---

**Questions?** Open an issue on your repo or reach out to the Zarr community!

**Good luck with your open source project! 🌟**
