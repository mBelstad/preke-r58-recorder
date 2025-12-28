# R58 Release System

This document describes the production-grade release and update system for R58 devices.

## Overview

The release system provides:
- **Versioned releases** using semantic versioning
- **Signed artifacts** using GPG for integrity verification
- **Update channels** (stable, beta, dev) for controlled rollout
- **Preflight checks** to validate system state before updates
- **Automatic rollback** on failure
- **Config/data migrations** between versions

## Directory Structure

```
/opt/r58-app/
├── releases/              # Versioned release directories
│   ├── v1.0.0/
│   │   ├── manifest.json  # Version, checksums, requirements
│   │   ├── packages/      # Backend and frontend code
│   │   ├── scripts/       # Install, upgrade, rollback
│   │   ├── migrations/    # Database migrations
│   │   └── venv/          # Python virtual environment
│   └── v1.1.0/
├── current -> releases/v1.1.0  # Symlink to active release
├── shared/                # Persisted across releases
│   ├── recordings/
│   ├── config/
│   │   ├── r58.env
│   │   └── update.conf
│   ├── db/
│   │   └── r58.db
│   └── logs/
├── keys/
│   └── r58-release.pub    # GPG public key for verification
└── scripts/               # Device-level scripts
    ├── preflight.sh
    ├── deploy.sh
    └── rollback.sh
```

## Building a Release

Use the build script to create release artifacts:

```bash
# Build a stable release
./scripts/build-release.sh -v v1.0.0 -c stable -s

# Build a beta release
./scripts/build-release.sh -v v1.1.0-beta.1 -c beta

# Build without signing (dev)
./scripts/build-release.sh -v v1.1.0-dev.42 -c dev
```

### Build Output

The script creates:
- `r58-v1.0.0-arm64.tar.gz` - Release tarball
- `r58-v1.0.0-arm64.tar.gz.sha256` - Checksum file
- `r58-v1.0.0-arm64.tar.gz.asc` - GPG signature (if signed)

## Release Manifest

Each release includes a `manifest.json`:

```json
{
  "version": "1.0.0",
  "channel": "stable",
  "build_date": "2025-12-28T10:00:00Z",
  "git_sha": "29b77f81",
  "arch": "arm64",
  "min_version": "0.9.0",
  "checksums": {
    "packages/backend": "sha256:abc123...",
    "packages/frontend": "sha256:def456..."
  },
  "requirements": {
    "python": ">=3.11",
    "disk_mb": 500,
    "ram_mb": 256
  },
  "migrations": ["001_add_alerts_table"]
}
```

## GPG Signing

### Generate a Signing Key

```bash
./scripts/sign-release.sh --generate-key
```

### Sign a Release

```bash
./scripts/sign-release.sh dist/r58-v1.0.0-arm64.tar.gz
```

### Verify a Release

```bash
./scripts/sign-release.sh --verify dist/r58-v1.0.0-arm64.tar.gz
```

### Export Public Key

```bash
./scripts/sign-release.sh --export-pub > r58-release.pub
```

## Update Channels

| Channel | Auto-update | Stability | Audience |
|---------|-------------|-----------|----------|
| stable  | Weekly      | Production| All customers |
| beta    | Daily       | Testing   | Internal testers |
| dev     | Hourly      | Unstable  | Developers only |

### Channel Configuration

Edit `/opt/r58-app/shared/config/update.conf`:

```bash
CHANNEL=stable
AUTO_UPDATE=false
CHECK_INTERVAL=86400  # 24 hours
UPDATE_WINDOW=02:00-06:00
```

## Deploying a Release

### Fresh Install

```bash
# Download and extract release
scp r58-v1.0.0-arm64.tar.gz user@device:/tmp/
ssh user@device "tar -xzf /tmp/r58-v1.0.0-arm64.tar.gz -C /tmp/"

# Run install script
ssh user@device "/tmp/r58-v1.0.0-arm64/scripts/install.sh"
```

### Upgrade

```bash
# Copy release to device
scp r58-v1.1.0-arm64.tar.gz user@device:/tmp/

# Extract and upgrade
ssh user@device "
  tar -xzf /tmp/r58-v1.1.0-arm64.tar.gz -C /tmp/
  /tmp/r58-v1.1.0-arm64/scripts/upgrade.sh
"
```

### Rollback

```bash
ssh user@device "/opt/r58-app/scripts/rollback.sh"
```

## Preflight Checks

Before any upgrade, the preflight script validates:

1. **Disk space** - Enough space for new release
2. **Python version** - Required Python version available
3. **Version compatibility** - Current version meets minimum requirement
4. **Service status** - R58 API is running
5. **No active recording** - Recording is not in progress
6. **RAM available** - Sufficient memory for upgrade
7. **Directory permissions** - Required directories are writable

Run manually:

```bash
/opt/r58-app/scripts/update-preflight.sh /path/to/manifest.json
```

## Database Migrations

Migrations are Python files in `migrations/`:

```python
# migrations/001_add_alerts_table.py
import sqlite3
from pathlib import Path

def migrate(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            level TEXT NOT NULL,
            message TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def rollback(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.execute("DROP TABLE IF EXISTS alerts")
    conn.commit()
    conn.close()
```

Migrations are tracked in the `_migrations` table and run automatically during upgrades.

## Automatic Rollback

The system automatically rolls back when:

1. Service fails to start within 60 seconds
2. Health check fails 3 times after update
3. Manual rollback is triggered

Rollback is atomic (symlink switch) and fast.

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Build Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build release
        run: ./scripts/build-release.sh -v ${{ github.ref_name }} -c stable
      
      - name: Sign release
        env:
          GPG_PRIVATE_KEY: ${{ secrets.GPG_PRIVATE_KEY }}
        run: |
          echo "$GPG_PRIVATE_KEY" | gpg --import
          ./scripts/sign-release.sh dist/r58-*.tar.gz
      
      - name: Upload to release server
        run: |
          curl -X POST https://releases.r58.itagenten.no/upload \
            -H "Authorization: Bearer ${{ secrets.RELEASE_TOKEN }}" \
            -F "artifact=@dist/r58-*.tar.gz" \
            -F "signature=@dist/r58-*.tar.gz.asc"
```

## Troubleshooting

### Release won't install

1. Check preflight: `/opt/r58-app/scripts/update-preflight.sh manifest.json`
2. Check disk space: `df -h /opt`
3. Check Python: `python3 --version`

### Signature verification fails

1. Import public key: `gpg --import /opt/r58-app/keys/r58-release.pub`
2. Check key fingerprint: `gpg --list-keys r58-release@itagenten.no`

### Rollback needed

```bash
# View available releases
ls -la /opt/r58-app/releases/

# Rollback to previous
/opt/r58-app/scripts/rollback.sh

# Check status
systemctl status r58-api
curl -s http://localhost:8000/api/v1/health
```

