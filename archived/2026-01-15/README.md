# Archived Code - January 15, 2026

## Overview

This directory contains code that was previously used but has been replaced or merged into the main codebase. The code is kept for reference but is no longer actively used.

## Archived Items

### `r58_api/` - Modular Backend API

**Date Archived**: January 15, 2026  
**Reason**: All features have been merged into `src/main.py`

**What was archived**:
- Complete modular FastAPI backend structure
- WordPress integration module (`control/wordpress/`)
- LAN discovery module (`control/lan_discovery/`)
- Capabilities endpoint (`control/devices/capabilities.py`)
- Various other control modules

**Why it was archived**:
- The device was running `src/main.py` as the active backend
- New features were added to `packages/backend/r58_api/` but never deployed
- To avoid confusion and ensure all features work, everything was merged into `src/main.py`
- This ensures a single source of truth for the backend

**Replacement**:
- All endpoints now exist in `src/main.py`
- WordPress integration: `src/wordpress.py` + endpoints in `src/main.py`
- LAN discovery: Endpoints in `src/main.py`
- Capabilities: Endpoint in `src/main.py`

**What was already removed** (before archival):
- `control/streaming.py` - Duplicated streaming endpoints
- `control/ptz_controller/router.py` - Duplicated PTZ endpoints
- `control/cameras/router.py` - Duplicated camera endpoints

## Reference

If you need to understand how a feature was originally implemented, you can reference this archived code. However, the active implementation in `src/main.py` is the source of truth.

## Migration Notes

The merge process ensured:
- ✅ All API endpoints preserved
- ✅ Same FastAPI/Pydantic patterns
- ✅ Same authentication/authorization
- ✅ Backward compatibility maintained

No breaking changes were introduced during the merge.
