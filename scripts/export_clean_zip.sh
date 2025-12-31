#!/bin/bash
# Clean Export Script
# Creates a production-ready ZIP excluding all ignored files

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║              CLEAN EXPORT SCRIPT                                  ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Run sanity check
echo "Step 1: Running sanity check..."
if ! bash scripts/repo_sanity_check.sh; then
    echo ""
    echo "❌ Sanity check failed. Fix issues before exporting."
    exit 1
fi

echo ""
echo "Step 2: Creating clean export..."

# Create dist directory
mkdir -p dist

# Output file
OUTPUT_FILE="dist/securityflash_suite_clean.zip"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE_TIMESTAMPED="dist/securityflash_suite_${TIMESTAMP}.zip"

# Check if git is available
if command -v git >/dev/null 2>&1 && [ -d .git ]; then
    echo "  Using git archive (respects .gitignore)..."
    git archive --format=zip --output="$OUTPUT_FILE" HEAD
    echo "  ✅ Created: $OUTPUT_FILE"
else
    echo "  Using zip with exclusions (no git repo)..."
    
    # Create zip with exclusions
    zip -r "$OUTPUT_FILE" . \
        -x "*.pyc" \
        -x "*__pycache__*" \
        -x "*node_modules*" \
        -x "*venv*" \
        -x "*.venv*" \
        -x "*ENV*" \
        -x "*.DS_Store*" \
        -x "*._**" \
        -x "*__MACOSX*" \
        -x "*.log" \
        -x "*dist/*" \
        -x "*.egg-info*" \
        -x "*.pytest_cache*" \
        -x "*htmlcov*" \
        -x "*.coverage" \
        -x "*.next*" \
        -x "*build/*" \
        -x "*.tsbuildinfo" \
        -x "*dump.rdb" \
        -x "*.sqlite*" \
        -x "*.db" \
        >/dev/null 2>&1
    
    echo "  ✅ Created: $OUTPUT_FILE"
fi

# Also create timestamped version
cp "$OUTPUT_FILE" "$OUTPUT_FILE_TIMESTAMPED"
echo "  ✅ Created: $OUTPUT_FILE_TIMESTAMPED"

# Get sizes
ORIGINAL_SIZE=$(du -sh . | cut -f1)
ZIP_SIZE=$(du -sh "$OUTPUT_FILE" | cut -f1)

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "EXPORT SUMMARY"
echo "═══════════════════════════════════════════════════════════════════"
echo "  Original repo size: $ORIGINAL_SIZE"
echo "  Clean ZIP size: $ZIP_SIZE"
echo "  Output: $OUTPUT_FILE"
echo "  Timestamped: $OUTPUT_FILE_TIMESTAMPED"
echo ""
echo "✅ Clean export complete!"
echo "═══════════════════════════════════════════════════════════════════"
