#!/bin/bash
# Repo-wide Sanity Check
# Ensures both securityflash/ and pentest-ai-platform/ are clean

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║              REPO-WIDE SANITY CHECK                               ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

FAILED=0

# Check 1: __MACOSX directories
echo "[1/8] Checking for __MACOSX directories..."
if find . -name "__MACOSX" -type d 2>/dev/null | grep -q .; then
    echo "❌ FAIL: Found __MACOSX directories:"
    find . -name "__MACOSX" -type d
    FAILED=1
else
    echo "✅ PASS: No __MACOSX directories"
fi
echo ""

# Check 2: .DS_Store files
echo "[2/8] Checking for .DS_Store files..."
if find . -name ".DS_Store" -type f 2>/dev/null | grep -q .; then
    echo "❌ FAIL: Found .DS_Store files:"
    find . -name ".DS_Store" -type f | head -10
    FAILED=1
else
    echo "✅ PASS: No .DS_Store files"
fi
echo ""

# Check 3: AppleDouble files (._*)
echo "[3/8] Checking for AppleDouble files (._*)..."
if find . -name "._*" -type f 2>/dev/null | grep -q .; then
    echo "❌ FAIL: Found AppleDouble files:"
    find . -name "._*" -type f | head -10
    FAILED=1
else
    echo "✅ PASS: No AppleDouble files"
fi
echo ""

# Check 4: venv directories
echo "[4/8] Checking for venv/ENV/.venv directories..."
if find . -name "venv" -o -name ".venv" -o -name "ENV" | grep -q .; then
    echo "❌ FAIL: Found virtual environment directories:"
    find . -name "venv" -o -name ".venv" -o -name "ENV"
    FAILED=1
else
    echo "✅ PASS: No venv directories"
fi
echo ""

# Check 5: node_modules
echo "[5/8] Checking for node_modules directories..."
if find . -name "node_modules" -type d 2>/dev/null | grep -q .; then
    echo "❌ FAIL: Found node_modules directories:"
    find . -name "node_modules" -type d
    FAILED=1
else
    echo "✅ PASS: No node_modules directories"
fi
echo ""

# Check 6: Nested archives
echo "[6/8] Checking for nested archives (*.tar.gz, *.zip)..."
if find . -maxdepth 3 \( -name "*.tar.gz" -o -name "*.zip" \) -type f 2>/dev/null | grep -q .; then
    echo "❌ FAIL: Found nested archives:"
    find . -maxdepth 3 \( -name "*.tar.gz" -o -name "*.zip" \) -type f
    FAILED=1
else
    echo "✅ PASS: No nested archives"
fi
echo ""

# Check 7: .gitignore files exist
echo "[7/8] Checking for .gitignore files..."
GITIGNORE_MISSING=0
if [ ! -f "securityflash/.gitignore" ]; then
    echo "❌ FAIL: securityflash/.gitignore missing"
    GITIGNORE_MISSING=1
fi
if [ ! -f "pentest-ai-platform/.gitignore" ]; then
    echo "❌ FAIL: pentest-ai-platform/.gitignore missing"
    GITIGNORE_MISSING=1
fi
if [ $GITIGNORE_MISSING -eq 0 ]; then
    echo "✅ PASS: Both .gitignore files exist"
else
    FAILED=1
fi
echo ""

# Check 8: Repo size
echo "[8/8] Repository size summary..."
TOTAL_SIZE=$(du -sh . 2>/dev/null | cut -f1)
SECURITYFLASH_SIZE=$(du -sh securityflash 2>/dev/null | cut -f1)
PENTEST_SIZE=$(du -sh pentest-ai-platform 2>/dev/null | cut -f1)

echo "  Total repo size: $TOTAL_SIZE"
echo "  securityflash/: $SECURITYFLASH_SIZE"
echo "  pentest-ai-platform/: $PENTEST_SIZE"
echo "✅ PASS: Size check complete"
echo ""

# Top-level tree
echo "═══════════════════════════════════════════════════════════════════"
echo "TOP-LEVEL TREE (depth 2)"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Manual tree implementation (depth 2)
echo "."
ls -1 | while read item; do
    if [ -d "$item" ]; then
        echo "├── $item/"
        if [ "$item" = "securityflash" ] || [ "$item" = "pentest-ai-platform" ] || [ "$item" = "scripts" ]; then
            ls -1 "$item" 2>/dev/null | head -10 | while read subitem; do
                if [ -d "$item/$subitem" ]; then
                    echo "│   ├── $subitem/"
                else
                    echo "│   ├── $subitem"
                fi
            done
        fi
    else
        echo "├── $item"
    fi
done

echo ""
echo "═══════════════════════════════════════════════════════════════════"

# Summary
if [ $FAILED -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED - Repository is clean"
    echo "═══════════════════════════════════════════════════════════════════"
    exit 0
else
    echo "❌ SOME CHECKS FAILED - Fix issues above"
    echo "═══════════════════════════════════════════════════════════════════"
    exit 1
fi
