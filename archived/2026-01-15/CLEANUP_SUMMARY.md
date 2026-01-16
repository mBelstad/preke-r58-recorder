# Cleanup Summary - January 15, 2026

## Completed Cleanup

### Archived
- ✅ `packages/backend/r58_api/` - Moved to `archived/2026-01-15/`
  - All features merged into `src/main.py`
  - No longer needed as separate module

### Already Removed (Previous Cleanup)
- ✅ `packages/backend/r58_api/control/streaming.py` - Duplicate streaming endpoints
- ✅ `packages/backend/r58_api/control/ptz_controller/` - Duplicate PTZ endpoints  
- ✅ `packages/backend/r58_api/control/cameras/` - Duplicate camera endpoints

## Still Active (Do Not Remove)

### `packages/backend/pipeline_manager/`
**Status**: ✅ ACTIVE - Still used by main application
- Used by: `src/main.py`, `src/pipelines.py`, `src/recorder.py`, `src/ingest.py`
- Purpose: GStreamer pipeline management
- **Keep**: This is core functionality

### Test Files
**Status**: ⚠️ REVIEW - Some may be outdated
- Root level test files (`test_*.html`, `test_*.py`) - May be for manual testing
- `packages/backend/tests/` - Unit tests for pipeline_manager (keep)
- `tests/test_scenes.py` - Scene tests (keep)

**Recommendation**: Review root-level test files individually before removing

### Fleet Directory
**Status**: ⚠️ PLACEHOLDER - Not actively used
- Only referenced in wiki and as placeholder in capabilities endpoint
- No active imports or usage found
- **Action**: Can be archived if not planning to use fleet management

### Coolify Directory
**Status**: ⚠️ DEPLOYMENT - May still be used
- Contains deployment scripts and configs
- **Action**: Keep unless confirmed unused

## Recommendations

1. **Keep**: `packages/backend/pipeline_manager/` - Core functionality
2. **Review**: Root-level test files - May be useful for manual testing
3. **Archive if unused**: `fleet/` directory - Only placeholder references
4. **Keep**: `coolify/` - Deployment infrastructure

## No Breaking Changes

All cleanup was done without breaking existing functionality:
- ✅ No imports broken
- ✅ All active code preserved
- ✅ Only unused/duplicate code archived
