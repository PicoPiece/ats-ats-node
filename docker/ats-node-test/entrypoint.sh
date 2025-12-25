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

# Validate manifest exists
if [ ! -f "$MANIFEST_PATH" ]; then
    echo "❌ Manifest not found: ${MANIFEST_PATH}"
    exit 1
fi

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

