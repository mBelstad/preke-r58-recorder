"""
Release management endpoints for Fleet Management.
"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models.schemas import (
    Release,
    ReleaseCreate,
    ReleaseLatest,
    UpdateChannel,
    PaginatedResponse,
)
from .auth import get_current_user, require_role

logger = logging.getLogger(__name__)
router = APIRouter()


# In-memory release storage (replace with actual database)
_releases: List[dict] = [
    {
        "id": str(uuid4()),
        "version": "1.0.0",
        "channel": UpdateChannel.STABLE,
        "build_date": datetime(2025, 12, 28, 10, 0, 0),
        "git_sha": "29b77f81",
        "artifact_url": f"{settings.releases_base_url}/releases/v1.0.0/r58-v1.0.0-arm64.tar.gz",
        "signature_url": f"{settings.releases_base_url}/releases/v1.0.0/r58-v1.0.0-arm64.tar.gz.asc",
        "checksum_sha256": "abc123def456789...",
        "size_bytes": 52428800,  # 50MB
        "min_version": None,
        "arch": "arm64",
        "changelog": "Initial stable release",
        "release_notes": "First production release of R58 system.",
        "manifest": {},
        "is_active": True,
        "is_latest": True,
        "created_at": datetime(2025, 12, 28, 10, 0, 0),
        "published_at": datetime(2025, 12, 28, 12, 0, 0),
    }
]


@router.get("/releases/latest", response_model=ReleaseLatest)
async def get_latest_release(
    channel: UpdateChannel = Query(UpdateChannel.STABLE),
    arch: str = Query("arm64"),
):
    """
    Get the latest release for a channel.
    
    This endpoint is used by devices to check for updates.
    No authentication required.
    """
    # Find latest active release for channel
    channel_releases = [
        r for r in _releases
        if r["channel"] == channel
        and r["arch"] == arch
        and r["is_active"]
    ]
    
    if not channel_releases:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active releases found for channel {channel.value}",
        )
    
    # Sort by version (newest first) - simple string sort works for semver
    channel_releases.sort(key=lambda r: r["version"], reverse=True)
    latest = channel_releases[0]
    
    return ReleaseLatest(
        version=latest["version"],
        channel=latest["channel"].value,
        download_url=latest["artifact_url"],
        signature_url=latest.get("signature_url"),
        checksum_sha256=latest["checksum_sha256"],
        size_bytes=latest.get("size_bytes"),
        changelog=latest.get("changelog"),
    )


@router.get("/releases", response_model=PaginatedResponse)
async def list_releases(
    channel: Optional[UpdateChannel] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    """
    List all releases.
    """
    releases = _releases.copy()
    
    # Filter by channel
    if channel:
        releases = [r for r in releases if r["channel"] == channel]
    
    # Sort by version (newest first)
    releases.sort(key=lambda r: r["version"], reverse=True)
    
    # Paginate
    total = len(releases)
    start = (page - 1) * page_size
    end = start + page_size
    page_releases = releases[start:end]
    
    return PaginatedResponse(
        items=page_releases,
        total=total,
        page=page,
        page_size=page_size,
        has_more=end < total,
    )


@router.get("/releases/{version}", response_model=Release)
async def get_release(
    version: str,
    user: dict = Depends(get_current_user),
):
    """
    Get details of a specific release.
    """
    # Strip 'v' prefix if present
    version = version.lstrip("v")
    
    for release in _releases:
        if release["version"] == version:
            return Release(
                id=UUID(release["id"]),
                version=release["version"],
                channel=release["channel"],
                artifact_url=release["artifact_url"],
                signature_url=release.get("signature_url"),
                checksum_sha256=release["checksum_sha256"],
                size_bytes=release.get("size_bytes"),
                min_version=release.get("min_version"),
                changelog=release.get("changelog"),
                release_notes=release.get("release_notes"),
                manifest=release.get("manifest"),
                build_date=release.get("build_date"),
                git_sha=release.get("git_sha"),
                arch=release.get("arch", "arm64"),
                is_active=release.get("is_active", True),
                is_latest=release.get("is_latest", False),
                created_at=release["created_at"],
                published_at=release.get("published_at"),
            )
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Release {version} not found",
    )


@router.post("/releases", response_model=Release)
async def create_release(
    release: ReleaseCreate,
    user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new release.
    
    This is typically called by the CI/CD pipeline after building a release.
    Requires admin privileges.
    """
    # Check if version already exists
    for r in _releases:
        if r["version"] == release.version.lstrip("v"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Release {release.version} already exists",
            )
    
    # Create release record
    release_record = {
        "id": str(uuid4()),
        "version": release.version.lstrip("v"),
        "channel": release.channel,
        "build_date": datetime.utcnow(),
        "git_sha": None,
        "artifact_url": release.artifact_url,
        "signature_url": release.signature_url,
        "checksum_sha256": release.checksum_sha256,
        "size_bytes": release.size_bytes,
        "min_version": release.min_version,
        "arch": "arm64",
        "changelog": release.changelog,
        "release_notes": release.release_notes,
        "manifest": release.manifest,
        "is_active": True,
        "is_latest": False,
        "created_at": datetime.utcnow(),
        "published_at": None,
    }
    
    _releases.append(release_record)
    
    logger.info(f"Created release {release.version} in channel {release.channel}")
    
    return Release(
        id=UUID(release_record["id"]),
        version=release_record["version"],
        channel=release_record["channel"],
        artifact_url=release_record["artifact_url"],
        signature_url=release_record.get("signature_url"),
        checksum_sha256=release_record["checksum_sha256"],
        size_bytes=release_record.get("size_bytes"),
        min_version=release_record.get("min_version"),
        changelog=release_record.get("changelog"),
        release_notes=release_record.get("release_notes"),
        manifest=release_record.get("manifest"),
        build_date=release_record.get("build_date"),
        arch=release_record.get("arch", "arm64"),
        is_active=release_record.get("is_active", True),
        is_latest=release_record.get("is_latest", False),
        created_at=release_record["created_at"],
        published_at=release_record.get("published_at"),
    )


@router.post("/releases/{version}/publish", response_model=Release)
async def publish_release(
    version: str,
    user: dict = Depends(require_role("admin")),
):
    """
    Publish a release, making it the latest for its channel.
    
    Requires admin privileges.
    """
    version = version.lstrip("v")
    
    release = None
    for r in _releases:
        if r["version"] == version:
            release = r
            break
    
    if not release:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Release {version} not found",
        )
    
    # Unmark other releases in same channel as not latest
    for r in _releases:
        if r["channel"] == release["channel"]:
            r["is_latest"] = False
    
    # Mark this release as latest and published
    release["is_latest"] = True
    release["published_at"] = datetime.utcnow()
    
    logger.info(f"Published release {version} as latest in {release['channel']}")
    
    return Release(
        id=UUID(release["id"]),
        version=release["version"],
        channel=release["channel"],
        artifact_url=release["artifact_url"],
        signature_url=release.get("signature_url"),
        checksum_sha256=release["checksum_sha256"],
        size_bytes=release.get("size_bytes"),
        is_active=release.get("is_active", True),
        is_latest=release.get("is_latest", False),
        created_at=release["created_at"],
        published_at=release.get("published_at"),
    )


@router.delete("/releases/{version}", status_code=status.HTTP_204_NO_CONTENT)
async def deprecate_release(
    version: str,
    user: dict = Depends(require_role("admin")),
):
    """
    Deprecate a release, marking it as inactive.
    
    Deprecated releases cannot be downloaded.
    Requires admin privileges.
    """
    version = version.lstrip("v")
    
    for r in _releases:
        if r["version"] == version:
            r["is_active"] = False
            r["deprecated_at"] = datetime.utcnow()
            logger.warning(f"Deprecated release {version}")
            return
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Release {version} not found",
    )

