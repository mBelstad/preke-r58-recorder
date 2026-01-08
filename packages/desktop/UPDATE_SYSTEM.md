# Auto-Update System

The Preke Studio Electron app now includes automatic update functionality using GitHub Releases.

## How It Works

1. **Automatic Check**: The app checks for updates 5 seconds after startup
2. **Manual Check**: Users can check for updates via the menu (App > Check for Updates...)
3. **Notification**: When an update is available, a banner appears at the top of the app
4. **Download**: Users can download the update with one click
5. **Install**: After download, users can install and restart with one click

## Publishing Updates

### Prerequisites

1. **GitHub Token**: You need a GitHub Personal Access Token with `repo` scope
   - Go to GitHub Settings > Developer settings > Personal access tokens
   - Create a token with `repo` scope
   - Store it securely (use environment variable or GitHub Secrets for CI/CD)

2. **Version Bump**: Update the version in `package.json` before building

### Publishing Process

1. **Update Version**:
   ```bash
   cd packages/desktop
   # Edit package.json and increment version (e.g., 2.0.0 -> 2.0.1)
   ```

2. **Build Distributables**:
   ```bash
   npm run dist:all
   # This creates:
   # - dist/Preke Studio-2.0.1-universal.dmg (macOS)
   # - dist/Preke Studio Setup 2.0.1.exe (Windows)
   ```

3. **Publish to GitHub** (Option A - Manual):
   - Go to https://github.com/mBelstad/preke-r58-recorder/releases/new
   - Create a new release with tag `v2.0.1` (must match version)
   - Upload the DMG and EXE files
   - Add release notes
   - Publish the release

4. **Publish to GitHub** (Option B - Automated):
   ```bash
   # Set GitHub token
   export GH_TOKEN=your_github_token_here
   
   # Build and publish
   npm run dist:all
   npx electron-builder --publish always
   ```
   This will automatically:
   - Build the app
   - Create a GitHub release
   - Upload the DMG and EXE files
   - Publish the release

### Version Format

- Use semantic versioning: `MAJOR.MINOR.PATCH` (e.g., `2.0.1`)
- The version in `package.json` must match the GitHub release tag (prefixed with `v`)
- Example: `package.json` version `2.0.1` → GitHub release tag `v2.0.1`

## User Experience

### Update Notification Banner

When an update is available, users see a banner at the top of the app with:
- Update version number
- Download button
- Progress bar during download
- Install & Restart button when ready

### Update Flow

1. **Check**: App automatically checks on startup (after 5 seconds)
2. **Notify**: Banner appears if update is available
3. **Download**: User clicks "Download" → progress bar shows download status
4. **Install**: User clicks "Install & Restart" → app closes, installs update, and restarts

### Menu Option

Users can manually check for updates:
- **macOS**: App menu > Check for Updates...
- **Windows**: File menu > Check for Updates...

## Configuration

The update system is configured in:
- `electron-builder.yml`: GitHub publisher settings
- `src/main/updater.ts`: Update logic and event handling
- `src/main/index.ts`: IPC handlers and startup check
- `src/preload/index.ts`: Renderer API exposure
- `src/components/shared/UpdateNotification.vue`: UI component

## Testing Updates

To test the update system:

1. **Build current version** (e.g., 2.0.0):
   ```bash
   npm run dist:all
   ```

2. **Install and run** the app

3. **Create a test release**:
   - Bump version to 2.0.1 in `package.json`
   - Build again: `npm run dist:all`
   - Create GitHub release with tag `v2.0.1`
   - Upload the new DMG/EXE

4. **Test in app**:
   - The app should detect the update
   - Download and install should work

## Troubleshooting

### Updates Not Detected

- Verify GitHub release tag matches version (e.g., `v2.0.1` for version `2.0.1`)
- Check that DMG/EXE files are uploaded to the release
- Verify GitHub token has `repo` scope
- Check app logs for update errors

### Download Fails

- Check internet connection
- Verify GitHub release is public (or token has access)
- Check app logs for specific error messages

### Install Fails

- Ensure app has write permissions
- On macOS, may need to allow app in System Preferences > Security
- Check app logs for installation errors

## Security Notes

- Updates are verified using GitHub's release signatures
- Only releases from the configured repository are accepted
- Users should verify the publisher matches before installing

## Future Enhancements

- [ ] Staged rollouts (update to % of users)
- [ ] Update channels (stable, beta, alpha)
- [ ] Delta updates (smaller download sizes)
- [ ] Update scheduling (install on next launch)
