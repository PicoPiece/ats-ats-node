#!/bin/bash
# ATS Node Test Execution Entrypoint
# This script orchestrates the entire test execution:
# 1. Load manifest
# 2. Flash firmware
# 3. Run tests
# 4. Write results

set -e

MANIFEST_PATH="${MANIFEST_PATH:-/workspace/ats-manifest.yaml}"
RESULTS_DIR="${RESULTS_DIR:-/workspace/results}"

echo "🚀 [ATS Node] Starting test execution"
echo "📋 Manifest: ${MANIFEST_PATH}"
echo "📊 Results: ${RESULTS_DIR}"
echo ""

# CRITICAL: Check if /workspace is mounted BEFORE anything else
echo "🔍 Step 1: Checking workspace mount..."
if [ ! -d "/workspace" ]; then
    echo "❌ CRITICAL: /workspace directory does NOT exist!"
    echo "   This means volume mount failed or path is wrong."
    echo "   Container cannot proceed without workspace mount."
    exit 1
fi

echo "✅ /workspace directory exists"
echo "   Contents:"
ls -lah /workspace/ 2>&1 | head -15 || echo "   (cannot list)"
echo ""

# Debug: Show container environment
echo "🔍 Container debug info:"
echo "   User: $(whoami)"
echo "   UID: $(id -u)"
echo "   GID: $(id -g)"
echo "   Working directory: $(pwd)"
echo "   MANIFEST_PATH: ${MANIFEST_PATH}"
echo ""
echo "   Checking if /workspace exists:"
if [ -d "/workspace" ]; then
    echo "   ✅ /workspace directory exists"
    echo "   Workspace contents:"
    ls -lah /workspace/ 2>&1 | head -20 || true
    echo ""
    echo "   Looking for manifest files:"
    find /workspace -name "*manifest*" -o -name "*.yaml" 2>&1 | head -10 || true
else
    echo "   ❌ /workspace directory does NOT exist!"
fi
echo ""

# Validate manifest exists - try multiple methods
MANIFEST_FOUND=false

# Method 1: test -f
if [ -f "$MANIFEST_PATH" ]; then
    MANIFEST_FOUND=true
fi

# Method 2: test -r (readable)
if [ -r "$MANIFEST_PATH" ]; then
    MANIFEST_FOUND=true
fi

# Method 3: try to read first line
if head -n 1 "$MANIFEST_PATH" > /dev/null 2>&1; then
    MANIFEST_FOUND=true
fi

if [ "$MANIFEST_FOUND" = false ]; then
    echo "❌ Manifest not found or not accessible: ${MANIFEST_PATH}"
    echo ""
    echo "🔍 Debugging:"
    echo "   Checking if path exists:"
    ls -lah "$MANIFEST_PATH" 2>&1 || echo "   Path does not exist"
    echo ""
    echo "   Checking workspace directory:"
    ls -lah /workspace/ 2>&1 || echo "   /workspace does not exist"
    echo ""
    echo "   Checking if file exists with different case:"
    find /workspace -iname "*manifest*" 2>&1 || echo "   No manifest files found"
    echo ""
    echo "   Trying to read file directly:"
    cat "$MANIFEST_PATH" 2>&1 || echo "   Cannot read file"
    exit 1
fi

echo "✅ Manifest found and accessible"

# Create results directory
mkdir -p "$RESULTS_DIR"

# Execute test orchestration
python3 -m ats_node_test.executor \
    --manifest "$MANIFEST_PATH" \
    --results-dir "$RESULTS_DIR" \
    --workspace /workspace

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ [ATS Node] Test execution completed successfully"
else
    echo "❌ [ATS Node] Test execution failed (exit code: ${EXIT_CODE})"
fi

exit $EXIT_CODE

