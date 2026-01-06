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

# Check if buildx is available for multi-arch builds
if docker buildx version > /dev/null 2>&1; then
    echo "📦 Using buildx for multi-architecture build (amd64, arm64)..."
    
    # Create builder if it doesn't exist
    if ! docker buildx inspect ats-builder > /dev/null 2>&1; then
        echo "🔧 Creating buildx builder..."
        docker buildx create --name ats-builder --use
        docker buildx inspect --bootstrap
    else
        docker buildx use ats-builder
    fi
    
    # Build and push multi-arch image
    echo "🏗️  Building for linux/amd64,linux/arm64..."
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --tag "${FULL_IMAGE}" \
        --push \
        .
    
    echo "✅ Multi-arch image built and pushed: ${FULL_IMAGE}"
    echo "   Supports: amd64 (Xeon server) and arm64 (Raspberry Pi)"
    
    # Also tag locally for amd64 (current machine)
    docker pull "${FULL_IMAGE}" --platform linux/amd64
    docker tag "${FULL_IMAGE}" "ats-node-test:latest"
else
    echo "⚠️  buildx not available, building for current platform only"
    echo "   For Raspberry Pi support, install buildx: https://docs.docker.com/buildx/working-with-buildx/"
    docker build -t "${FULL_IMAGE}" .
fi

# Tag as latest locally too (only if not using buildx)
if ! docker buildx version > /dev/null 2>&1; then
    docker tag "${FULL_IMAGE}" "ats-node-test:latest"
fi

echo ""
echo "✅ Image built: ${FULL_IMAGE}"
echo ""

# Ask if user wants to push (skip if already pushed via buildx)
if docker buildx version > /dev/null 2>&1 && docker buildx inspect ats-builder > /dev/null 2>&1; then
    echo ""
    echo "✅ Image already pushed via buildx (multi-arch)"
    PUSH_SKIP=true
else
    PUSH_SKIP=false
fi

# Ask if user wants to push
if [ "$PUSH_SKIP" = false ]; then
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
        echo ""
        echo "🔓 To make image public (for CI without auth):"
        echo "   gh api user/packages/container/ats-node-test -X PATCH -f visibility=public"
        echo "   Or: GitHub → Packages → ats-node-test → Package settings → Change visibility → Public"
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
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Done"

