#!/bin/bash
# Quick Script to Publish CryoET Extension to GitHub
# Run this after reviewing all files!

set -e  # Exit on any error

echo "================================================"
echo "🚀 Publishing Zarr-Benchmarks CryoET Extension"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if in correct directory
if [ ! -f "cryoet_real_data_quick.py" ]; then
    echo "❌ Error: Run this script from the zarr-benchmarks directory!"
    exit 1
fi

echo -e "${BLUE}Step 1: Creating/updating .gitignore${NC}"
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/
env/

# Jupyter
.ipynb_checkpoints/

# macOS
.DS_Store

# IDE
.vscode/
.idea/

# Large files (keep examples only)
*.zarr/
!data/output/**/*.png
!data/output/**/*.csv

# Logs
*.log
EOF

echo -e "${GREEN}✓ .gitignore created${NC}"
echo ""

echo -e "${BLUE}Step 2: Staging all CryoET extension files${NC}"

# Add documentation
git add *.md

# Add scripts
git add cryoet_*.py
git add test_cryoet_connection_v2.py

# Add notebooks
git add comprehensive_cryoet_notebook.ipynb
git add cryoet_portal_benchmark.ipynb

# Add requirements
git add requirements-cryoet.txt

# Add GitHub workflows
git add .github/workflows/cryoet-benchmarks.yml

# Add example outputs (small files only)
git add data/output/**/*.png 2>/dev/null || true
git add data/output/**/*.csv 2>/dev/null || true

echo -e "${GREEN}✓ Files staged${NC}"
echo ""

echo -e "${BLUE}Step 3: Showing what will be committed${NC}"
git status --short
echo ""

echo -e "${YELLOW}Review the above files. Press ENTER to continue or Ctrl+C to cancel${NC}"
read -r

echo -e "${BLUE}Step 4: Creating commit${NC}"
git commit -m "feat: add comprehensive CryoET benchmarking extension

Major features:
- Real CryoET data integration via Data Portal API (Dataset 10445)
- Compression benchmarks: Blosc-Zstd, LZ4, Zstd, GZip
- Chunking analysis: 16³ to 128³, cubic and non-cubic
- 8 comprehensive documentation files
- 3 Jupyter notebooks for interactive exploration
- CI/CD pipeline with GitHub Actions
- Example visualizations and results

Key findings:
- Blosc-Zstd: 1.17× compression, 14.4% storage savings
- 64³ chunks: optimal balance for general use
- Non-cubic (16,128,128): 4× faster slice viewing
- 99.6% file reduction possible (16³ → 128³ chunks)
- Cloud storage cost savings: ~\$1000/year at repository scale

Documentation:
- TECHNICAL_REPORT.md: Full compression analysis
- CHUNKING_SHARDING_REPORT.md: Complete chunking study
- EXECUTIVE_SUMMARY.md: Quick reference guide
- CONTRIBUTING.md: Contribution guidelines
- ROADMAP.md: Future development plans
- GALLERY.md: Visual outputs showcase

Scripts ready for production use on any CryoET dataset.
Built on HEFTIE zarr-benchmarks framework.
"

echo -e "${GREEN}✓ Commit created${NC}"
echo ""

echo -e "${BLUE}Step 5: Setting up remote (if needed)${NC}"
echo "What would you like to do?"
echo "1) Create NEW repository: zarr-benchmarks-cryoet"
echo "2) Push to existing HEFTIE fork"
echo "3) Skip (I'll do it manually)"
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}Creating new repository...${NC}"
        echo "Repository: https://github.com/MaadhavKothari/zarr-benchmarks-cryoet"
        echo ""
        echo "Do you have GitHub CLI installed? (gh --version)"
        read -p "Use GitHub CLI? (y/n): " use_gh

        if [ "$use_gh" = "y" ]; then
            echo "Creating repository with GitHub CLI..."
            gh repo create zarr-benchmarks-cryoet \
                --public \
                --description "Comprehensive Zarr storage optimization for CryoET data - compression, chunking, sharding analysis" \
                --homepage "https://cryoetdataportal.czscience.com" \
                --source=. \
                --push

            echo -e "${GREEN}✓ Repository created and pushed!${NC}"
        else
            echo ""
            echo "Manual steps:"
            echo "1. Go to: https://github.com/new"
            echo "2. Name: zarr-benchmarks-cryoet"
            echo "3. Description: Comprehensive Zarr storage optimization for CryoET data"
            echo "4. Public: ✓"
            echo "5. DO NOT initialize with README"
            echo "6. Click 'Create repository'"
            echo ""
            echo "Then run these commands:"
            echo "git remote add cryoet https://github.com/MaadhavKothari/zarr-benchmarks-cryoet.git"
            echo "git push -u cryoet main"
        fi
        ;;
    2)
        echo "Pushing to existing HEFTIE fork origin..."
        git push origin main
        echo -e "${GREEN}✓ Pushed to origin${NC}"
        ;;
    3)
        echo "Skipping remote setup. You can push manually later."
        ;;
esac

echo ""
echo "================================================"
echo -e "${GREEN}🎉 SUCCESS!${NC}"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Visit your repository on GitHub"
echo "2. Add topics/tags: zarr, cryoet, benchmarking, etc."
echo "3. Setup GitHub Pages (Settings → Pages → main branch)"
echo "4. Create first release (v1.0.0)"
echo "5. Announce on Zarr Discourse!"
echo ""
echo "📚 See GITHUB_PUBLISHING_TUTORIAL.md for detailed guide"
echo ""
echo -e "${GREEN}Your work is now ready to make an impact! 🚀${NC}"

# Add newly created files
git add cryoet_advanced_benchmark.py
git add BIOIMAGETOOLS_INTEGRATION.md
git add QUICK_PUBLISH_GUIDE.md
git add GITHUB_PUBLISHING_TUTORIAL.md
git add GITHUB_READY_SUMMARY.md
git add GALLERY.md

