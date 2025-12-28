"""Release manifest schema and validation"""
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path
import json
import hashlib

from pydantic import BaseModel, Field, field_validator


class ReleaseRequirements(BaseModel):
    """System requirements for a release"""
    python: str = Field(default=">=3.11", description="Python version requirement")
    disk_mb: int = Field(default=500, description="Required disk space in MB")
    ram_mb: int = Field(default=256, description="Required RAM in MB")


class ReleaseChecksums(BaseModel):
    """Checksums for release components"""
    packages_backend: str = Field(alias="packages/backend")
    packages_frontend: Optional[str] = Field(default=None, alias="packages/frontend")
    
    class Config:
        populate_by_name = True


class ReleaseManifest(BaseModel):
    """
    Release manifest schema.
    
    This represents the manifest.json included in each release artifact.
    """
    version: str = Field(..., description="Semantic version (e.g., 1.0.0)")
    channel: str = Field(default="stable", description="Release channel: stable, beta, dev")
    build_date: datetime = Field(default_factory=datetime.utcnow)
    git_sha: str = Field(..., description="Git commit SHA")
    arch: str = Field(default="arm64", description="Target architecture")
    min_version: Optional[str] = Field(default=None, description="Minimum version for upgrade")
    checksums: ReleaseChecksums
    requirements: ReleaseRequirements = Field(default_factory=ReleaseRequirements)
    migrations: List[str] = Field(default_factory=list, description="Migration files to run")
    
    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate semantic version format"""
        # Strip 'v' prefix if present
        v = v.lstrip("v")
        
        # Basic semver validation
        parts = v.split("-")[0].split(".")
        if len(parts) < 2 or len(parts) > 3:
            raise ValueError(f"Invalid version format: {v}")
        
        for part in parts:
            if not part.isdigit():
                raise ValueError(f"Invalid version component: {part}")
        
        return v
    
    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        """Validate release channel"""
        valid_channels = {"stable", "beta", "dev"}
        if v not in valid_channels:
            raise ValueError(f"Invalid channel: {v}. Must be one of: {valid_channels}")
        return v
    
    def is_compatible_upgrade(self, current_version: str) -> bool:
        """Check if this release can upgrade from current_version"""
        if not self.min_version:
            return True
        
        return self._compare_versions(current_version, self.min_version) >= 0
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two semantic versions.
        Returns: -1 if v1 < v2, 0 if equal, 1 if v1 > v2
        """
        def parse_version(v: str) -> tuple:
            # Strip prefix and pre-release
            v = v.lstrip("v").split("-")[0]
            parts = [int(x) for x in v.split(".")]
            # Pad to 3 parts
            while len(parts) < 3:
                parts.append(0)
            return tuple(parts)
        
        p1, p2 = parse_version(v1), parse_version(v2)
        
        if p1 < p2:
            return -1
        elif p1 > p2:
            return 1
        return 0
    
    @classmethod
    def from_file(cls, path: Path) -> "ReleaseManifest":
        """Load manifest from JSON file"""
        with open(path) as f:
            data = json.load(f)
        return cls(**data)
    
    def to_file(self, path: Path) -> None:
        """Save manifest to JSON file"""
        with open(path, "w") as f:
            json.dump(self.model_dump(by_alias=True), f, indent=2, default=str)


class ReleaseInfo(BaseModel):
    """
    Release information for update checking.
    
    This is the response from the update server's /releases/latest endpoint.
    """
    version: str
    channel: str
    build_date: datetime
    download_url: str
    signature_url: Optional[str] = None
    checksum_sha256: str
    size_bytes: int
    changelog_url: Optional[str] = None
    min_version: Optional[str] = None


class UpdateCheckRequest(BaseModel):
    """Request to check for updates"""
    current_version: str
    channel: str = "stable"
    arch: str = "arm64"
    device_id: Optional[str] = None


class UpdateCheckResponse(BaseModel):
    """Response from update check"""
    update_available: bool
    current_version: str
    latest_version: Optional[str] = None
    release: Optional[ReleaseInfo] = None
    message: Optional[str] = None


def verify_checksum(file_path: Path, expected_checksum: str) -> bool:
    """
    Verify file checksum.
    
    Args:
        file_path: Path to file to verify
        expected_checksum: Expected SHA256 checksum (with or without sha256: prefix)
    
    Returns:
        True if checksum matches, False otherwise
    """
    # Strip prefix if present
    expected = expected_checksum.replace("sha256:", "")
    
    # Calculate actual checksum
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    
    actual = sha256.hexdigest()
    return actual == expected


def verify_directory_checksum(dir_path: Path, expected_checksum: str) -> bool:
    """
    Verify checksum of all files in a directory.
    
    Calculates SHA256 of the concatenated checksums of all files.
    """
    expected = expected_checksum.replace("sha256:", "")
    
    # Get all files sorted by name
    files = sorted(dir_path.rglob("*"))
    files = [f for f in files if f.is_file()]
    
    # Calculate combined checksum
    combined = hashlib.sha256()
    for file_path in files:
        file_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                file_hash.update(chunk)
        combined.update(file_hash.hexdigest().encode())
    
    actual = combined.hexdigest()
    return actual == expected

