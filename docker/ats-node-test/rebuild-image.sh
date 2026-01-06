#!/bin/bash
# Rebuild ATS Node Test Docker Image
# Usage: ./rebuild-image.sh [tag] [push]
#   tag: Image tag (default: latest)
#   push: Push to registry after build (default: no)

set -e

IMAGE_NAME="ghcr.io/picopiece/ats-node-test"
TAG="${1:-latest}"
PUSH="${2:-no}"
FULL_IMAGE="${IMAGE_NAME}:${TAG}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐳 Rebuilding ATS Node Test Docker Image"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Image: ${FULL_IMAGE}"
echo "Tag: ${TAG}"
echo "Platform: $(uname -m)"
echo "Dockerfile: ${SCRIPT_DIR}/Dockerfile"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "   Please start Docker: sudo systemctl start docker"
    exit 1
fi

# Check if required files exist
if [ ! -f "Dockerfile" ]; then
    echo "❌ Error: Dockerfile not found at ${SCRIPT_DIR}/Dockerfile"
    exit 1
fi

if [ ! -f "entrypoint.sh" ]; then
    echo "❌ Error: entrypoint.sh not found at ${SCRIPT_DIR}/entrypoint.sh"
    exit 1
fi

if [ ! -d "ats_node_test" ]; then
    echo "❌ Error: ats_node_test directory not found at ${SCRIPT_DIR}/ats_node_test"
    exit 1
fi

echo "✅ All required files found"
echo ""

# Build image
echo "🔨 Building Docker image..."
echo "   This may take a few minutes..."
echo ""

docker build \
    --tag "${FULL_IMAGE}" \
    --platform linux/$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/') \
    .

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Image built successfully: ${FULL_IMAGE}"
    echo ""
    
    # Show image info
    echo "📋 Image information:"
    docker images "${FULL_IMAGE}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    echo ""
    
    # Ask about pushing
    if [ "$PUSH" = "yes" ] || [ "$PUSH" = "push" ]; then
        echo "📤 Pushing image to registry..."
        docker push "${FULL_IMAGE}"
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "✅ Image pushed successfully to ${FULL_IMAGE}"
        else
            echo ""
            echo "❌ Failed to push image"
            echo "   You may need to login first:"
            echo "   echo \$GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin"
            exit 1
        fi
    else
        echo "💡 To push this image to registry, run:"
        echo "   docker push ${FULL_IMAGE}"
        echo ""
        echo "   Or use this script with push option:"
        echo "   $0 ${TAG} push"
    fi
    
    echo ""
    echo "✅ Done!"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Test the image locally"
    echo "   2. Update Jenkins pipeline to use: ${FULL_IMAGE}"
    echo "   3. Push to registry if needed"
    
else
    echo ""
    echo "❌ Failed to build image"
    exit 1
fi

