#!/bin/bash
# =============================================================================
# R58 Release Signing Script
# Signs release artifacts with GPG and creates verification files
# =============================================================================
set -e

# Configuration
SIGNING_KEY="${GPG_SIGNING_KEY:-r58-release@itagenten.no}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] <release-file>

Sign a release artifact with GPG.

Options:
    -k, --key KEY_ID     GPG key ID or email to use for signing
                         Default: r58-release@itagenten.no
    -v, --verify         Verify existing signature instead of signing
    -g, --generate-key   Generate a new signing key pair
    -e, --export-pub     Export public key for distribution
    -h, --help           Show this help message

Examples:
    $(basename "$0") dist/r58-v1.0.0-arm64.tar.gz
    $(basename "$0") --verify dist/r58-v1.0.0-arm64.tar.gz
    $(basename "$0") --generate-key
    $(basename "$0") --export-pub > r58-release.pub
EOF
    exit 1
}

# Generate a new signing key
generate_key() {
    log_info "Generating new GPG signing key..."
    
    cat > /tmp/gpg-key-params << EOF
%echo Generating R58 release signing key
Key-Type: RSA
Key-Length: 4096
Subkey-Type: RSA
Subkey-Length: 4096
Name-Real: R58 Release Signing
Name-Email: r58-release@itagenten.no
Expire-Date: 2y
%no-protection
%commit
%echo Done
EOF
    
    gpg --batch --generate-key /tmp/gpg-key-params
    rm /tmp/gpg-key-params
    
    log_info "Key generated successfully!"
    log_info "Key ID: $(gpg --list-keys r58-release@itagenten.no | grep -A1 pub | tail -1 | xargs)"
    log_info ""
    log_info "To export for GitHub Secrets:"
    log_info "  gpg --export-secret-keys --armor r58-release@itagenten.no | base64"
    log_info ""
    log_info "To export public key for devices:"
    log_info "  gpg --export --armor r58-release@itagenten.no > r58-release.pub"
}

# Export public key
export_public_key() {
    if ! gpg --list-keys "$SIGNING_KEY" >/dev/null 2>&1; then
        log_error "Key not found: $SIGNING_KEY"
        exit 1
    fi
    
    gpg --export --armor "$SIGNING_KEY"
}

# Sign a release file
sign_release() {
    local RELEASE_FILE="$1"
    
    if [[ ! -f "$RELEASE_FILE" ]]; then
        log_error "File not found: $RELEASE_FILE"
        exit 1
    fi
    
    if ! gpg --list-keys "$SIGNING_KEY" >/dev/null 2>&1; then
        log_error "Signing key not found: $SIGNING_KEY"
        log_error "Generate one with: $(basename "$0") --generate-key"
        exit 1
    fi
    
    log_info "Signing: $RELEASE_FILE"
    log_info "Using key: $SIGNING_KEY"
    
    # Create detached signature
    gpg --armor --detach-sign -u "$SIGNING_KEY" "$RELEASE_FILE"
    
    SIGNATURE_FILE="${RELEASE_FILE}.asc"
    
    if [[ -f "$SIGNATURE_FILE" ]]; then
        log_info "Signature created: $SIGNATURE_FILE"
        
        # Verify immediately
        if gpg --verify "$SIGNATURE_FILE" "$RELEASE_FILE" 2>/dev/null; then
            log_info "Signature verified successfully!"
        else
            log_error "Signature verification failed!"
            exit 1
        fi
    else
        log_error "Failed to create signature"
        exit 1
    fi
    
    # Create checksum file if not exists
    CHECKSUM_FILE="${RELEASE_FILE}.sha256"
    if [[ ! -f "$CHECKSUM_FILE" ]]; then
        sha256sum "$RELEASE_FILE" > "$CHECKSUM_FILE"
        log_info "Checksum created: $CHECKSUM_FILE"
    fi
    
    echo ""
    log_info "Release signing complete!"
    log_info "Files:"
    log_info "  - $RELEASE_FILE"
    log_info "  - $SIGNATURE_FILE"
    log_info "  - $CHECKSUM_FILE"
}

# Verify a release signature
verify_release() {
    local RELEASE_FILE="$1"
    local SIGNATURE_FILE="${RELEASE_FILE}.asc"
    local CHECKSUM_FILE="${RELEASE_FILE}.sha256"
    
    if [[ ! -f "$RELEASE_FILE" ]]; then
        log_error "Release file not found: $RELEASE_FILE"
        exit 1
    fi
    
    local VERIFICATION_PASSED=true
    
    # Verify signature
    if [[ -f "$SIGNATURE_FILE" ]]; then
        log_info "Verifying GPG signature..."
        if gpg --verify "$SIGNATURE_FILE" "$RELEASE_FILE" 2>&1; then
            log_info "GPG signature: VALID"
        else
            log_error "GPG signature: INVALID"
            VERIFICATION_PASSED=false
        fi
    else
        log_warn "No signature file found: $SIGNATURE_FILE"
        VERIFICATION_PASSED=false
    fi
    
    # Verify checksum
    if [[ -f "$CHECKSUM_FILE" ]]; then
        log_info "Verifying SHA256 checksum..."
        if sha256sum -c "$CHECKSUM_FILE" >/dev/null 2>&1; then
            log_info "SHA256 checksum: VALID"
        else
            log_error "SHA256 checksum: INVALID"
            VERIFICATION_PASSED=false
        fi
    else
        log_warn "No checksum file found: $CHECKSUM_FILE"
    fi
    
    echo ""
    if $VERIFICATION_PASSED; then
        log_info "Verification PASSED"
        exit 0
    else
        log_error "Verification FAILED"
        exit 1
    fi
}

# Parse arguments
VERIFY=false
GENERATE=false
EXPORT=false
RELEASE_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -k|--key) SIGNING_KEY="$2"; shift 2 ;;
        -v|--verify) VERIFY=true; shift ;;
        -g|--generate-key) GENERATE=true; shift ;;
        -e|--export-pub) EXPORT=true; shift ;;
        -h|--help) usage ;;
        -*) log_error "Unknown option: $1"; usage ;;
        *) RELEASE_FILE="$1"; shift ;;
    esac
done

# Execute appropriate action
if $GENERATE; then
    generate_key
elif $EXPORT; then
    export_public_key
elif [[ -n "$RELEASE_FILE" ]]; then
    if $VERIFY; then
        verify_release "$RELEASE_FILE"
    else
        sign_release "$RELEASE_FILE"
    fi
else
    usage
fi

