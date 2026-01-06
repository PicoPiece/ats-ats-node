# GitHub Container Registry (GHCR) Setup

## Authentication

GitHub Container Registry requires authentication to push images.

### Option 1: Using GitHub Personal Access Token (Recommended)

1. **Create GitHub PAT:**
   - Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Generate new token with `write:packages` scope
   - Copy the token

2. **Login to GHCR:**
   ```bash
   echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
   ```

   Or interactively:
   ```bash
   docker login ghcr.io
   # Username: your-github-username
   # Password: your-github-token
   ```

3. **Verify login:**
   ```bash
   cat ~/.docker/config.json | grep ghcr.io
   ```

### Option 2: Using GitHub CLI

```bash
gh auth login
gh auth token | docker login ghcr.io -u USERNAME --password-stdin
```

## Push Image

After authentication:

```bash
cd docker/ats-node-test
./build-and-push.sh ghcr.io picopiece/ats-node-test latest
```

## Make Repository Public (Optional)

By default, GHCR repositories are private. To make public:

1. Go to GitHub → Your profile → Packages
2. Find `ats-node-test` package
3. Package settings → Change visibility → Public

Or use GitHub CLI:
```bash
gh api user/packages/container/ats-node-test -X PATCH -f visibility=public
```

## Troubleshooting

### Error: "denied"

- **Not authenticated**: Run `docker login ghcr.io`
- **Wrong credentials**: Check username and token
- **No permission**: Ensure token has `write:packages` scope
- **Repository doesn't exist**: First push will create it

### Error: "unauthorized"

- Token expired or invalid
- Token doesn't have required scopes
- Username/token mismatch

### Error: "repository name must be lowercase"

- Docker registry requires lowercase names
- Script auto-converts, but ensure you use lowercase in commands

## Using the Image

After pushing, use in Jenkins:

```groovy
ATS_NODE_TEST_IMAGE = 'ghcr.io/picopiece/ats-node-test:latest'
IMAGE_SOURCE = 'registry'
```

For public repositories, no authentication needed to pull.
For private repositories, Jenkins needs to authenticate.

