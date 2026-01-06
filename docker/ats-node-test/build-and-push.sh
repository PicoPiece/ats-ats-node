#!/bin/bash
# Build and push ats-node-test Docker image to registry
# Usage: ./build-and-push.sh [registry] [tag]

set -e

REGISTRY="${1:-ghcr.io}"
IMAGE_NAME="${2:-picopiece/ats-node-test}"
TAG="${3:-latest}"
# Convert to lowercase (Docker registry requirement)
IMAGE_NAME_LOWER=$(echo "${IMAGE_NAME}" | tr '[:upper:]' '[:lower:]')
FULL_IMAGE="${REGISTRY}/${IMAGE_NAME_LOWER}:${TAG}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🐳 Building and pushing ATS Node Test image"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Registry: ${REGISTRY}"
echo "Image: ${IMAGE_NAME} → ${IMAGE_NAME_LOWER} (lowercase)"
echo "Tag: ${TAG}"
echo "Full: ${FULL_IMAGE}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Build image
echo "🔨 Building Docker image..."
cd "$SCRIPT_DIR"
docker build -t "${FULL_IMAGE}" .

# Tag as latest locally too
docker tag "${FULL_IMAGE}" "ats-node-test:latest"

echo ""
echo "✅ Image built: ${FULL_IMAGE}"
echo ""

# Ask if user wants to push
read -p "Push to registry? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📤 Pushing to registry..."
    
    # Check if logged in to registry
    if [[ "${REGISTRY}" == "ghcr.io" ]]; then
        echo "🔐 Checking GitHub Container Registry authentication..."
        if ! docker pull "${FULL_IMAGE}" 2>/dev/null && ! echo "${FULL_IMAGE}" | grep -q "ghcr.io"; then
            echo ""
            echo "⚠️  Not authenticated to ghcr.io"
            echo ""
            echo "To authenticate:"
            echo "  1. Create GitHub Personal Access Token (PAT) with 'write:packages' scope"
            echo "  2. Run: echo \$GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin"
            echo ""
            echo "Or use:"
            echo "  docker login ghcr.io"
            echo "  Username: your-github-username"
            echo "  Password: your-github-token"
            echo ""
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "⏭️  Skipped push. Image available locally as: ${FULL_IMAGE}"
                exit 0
            fi
        fi
    fi
    
    if docker push "${FULL_IMAGE}"; then
        echo "✅ Image pushed: ${FULL_IMAGE}"
        echo ""
        echo "📝 To use this image, update Jenkinsfile.test:"
        echo "   ATS_NODE_TEST_IMAGE = '${FULL_IMAGE}'"
    else
        echo "❌ Failed to push image"
        echo ""
        echo "Common issues:"
        echo "  1. Not authenticated: docker login ${REGISTRY}"
        echo "  2. No permission to push to repository"
        echo "  3. Repository doesn't exist (create it first)"
        echo ""
        echo "Image is available locally as: ${FULL_IMAGE}"
    fi
else
    echo "⏭️  Skipped push. Image available locally as: ${FULL_IMAGE}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Done"

