# Building Docker Image for Raspberry Pi (ARM64)

## Problem

Docker images built on x86_64 machines won't run on Raspberry Pi (ARM64) by default. We need to build multi-architecture images.

## Solution: Use Docker Buildx

### 1. Install/Enable Buildx

Buildx comes with Docker Desktop and newer Docker versions. To check:

```bash
docker buildx version
```

If not available, install it:
```bash
# Linux
mkdir -p ~/.docker/cli-plugins
curl -L https://github.com/docker/buildx/releases/latest/download/buildx-v0.11.2.linux-amd64 -o ~/.docker/cli-plugins/docker-buildx
chmod +x ~/.docker/cli-plugins/docker-buildx
```

### 2. Build Multi-Arch Image

The `build-and-push.sh` script now automatically uses buildx to build for both architectures:

```bash
cd ats-ats-node/docker/ats-node-test
./build-and-push.sh ghcr.io picopiece/ats-node-test latest
```

This will:
- Build for `linux/amd64` (Xeon server)
- Build for `linux/arm64` (Raspberry Pi)
- Push both to registry as a single multi-arch manifest

### 3. Verify

After pushing, verify the image supports both architectures:

```bash
docker manifest inspect ghcr.io/picopiece/ats-node-test:latest
```

You should see both `amd64` and `arm64` in the output.

### 4. Test on Raspberry Pi

On your Raspberry Pi:

```bash
docker pull ghcr.io/picopiece/ats-node-test:latest
docker run --rm ghcr.io/picopiece/ats-node-test:latest --help
```

It should pull and run the ARM64 version automatically.

## Manual Build (Alternative)

If you want to build manually:

```bash
# Create builder
docker buildx create --name ats-builder --use
docker buildx inspect --bootstrap

# Build and push
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag ghcr.io/picopiece/ats-node-test:latest \
  --push \
  .

# Verify
docker manifest inspect ghcr.io/picopiece/ats-node-test:latest
```

## Troubleshooting

### "buildx not available"
- Install buildx (see step 1)
- Or use QEMU emulation (slower but works):
  ```bash
  docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
  ```

### "Cannot connect to Docker daemon"
- Ensure Docker is running
- Check permissions: `sudo usermod -aG docker $USER`

### Build fails on ARM64
- Some packages might not have ARM64 versions
- Check Dockerfile for architecture-specific dependencies
- Consider using multi-stage builds

## Current Status

✅ Script updated to use buildx automatically
✅ Supports both amd64 and arm64
✅ Single image tag works on both architectures

