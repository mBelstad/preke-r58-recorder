# Deploy HLS Fix - Remove MSE Code

## Quick Deploy Commands

SSH to R58 and run:

```bash
ssh linaro@r58.itagenten.no
# Password: linaro

cd /opt/preke-r58-recorder
sudo git fetch origin
sudo git reset --hard origin/feature/webrtc-switcher-preview
sudo chown -R linaro:linaro .
sudo systemctl restart preke-recorder
sleep 8
sudo systemctl status preke-recorder --no-pager | head -40
```

## What This Does

- Removes broken MSE implementation
- Restores working HLS streaming
- Cleans up protocol selector

## Verify

After restart, open: https://recorder.itagenten.no/

Should see:
- ✅ Cameras load and play
- ✅ HLS streams working
- ✅ No "Loading preview..." stuck state

## Status

- MSE commit reverted locally: ✅
- Force pushed to GitHub: ✅
- Ready to deploy: ✅
