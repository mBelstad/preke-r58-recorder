# Quick Start - DaVinci Automation

## Setup Complete! ✅

Both R58 device and your editing PC are configured and ready.

## Next Steps

### 1. Open DaVinci Resolve Studio
- Make sure DaVinci Resolve **Studio** (not free version) is running
- The automation service needs Resolve to be open to work

### 2. Start Automation Service

Once DaVinci Resolve is open, run:

```bash
cd "/Users/mariusbelstad/R58 app/preke-r58-recorder"
./start-davinci-automation.sh
```

Or manually:
```bash
python3 scripts/davinci-automation-service.py
```

You should see:
```
DaVinci Resolve Automation Service starting...
Webhook endpoints:
  POST /webhook/session-start
  POST /webhook/session-stop
  POST /webhook/file-added
  GET  /health
 * Running on http://0.0.0.0:8080
```

### 3. Test Health Endpoint

In another terminal, verify it's working:

```bash
curl http://localhost:8080/health
```

Should return:
```json
{
  "status": "healthy",
  "davinci_connected": true,
  "active_sessions": 0
}
```

### 4. Test with Recording

1. Go to https://app.itagenten.no
2. Start a recording session
3. Watch the automation service terminal - you should see:
   - Webhook received
   - Project created
   - Media imported
4. Check DaVinci Resolve - new project should appear!

## Configuration Summary

**R58 Device:**
- ✅ Automation enabled
- ✅ Webhook URL: `http://192.168.68.51:8080/webhook/session-start`
- ✅ Service restarted

**Editing PC:**
- ✅ Dependencies installed (flask, httpx, watchdog)
- ✅ DaVinci Scripting API available
- ✅ Ready to start service

## Troubleshooting

If `davinci_connected: false`:
- Ensure DaVinci Resolve Studio (not free) is running
- Restart DaVinci Resolve
- Restart automation service

If webhooks not received:
- Check firewall allows port 8080
- Verify R58 can reach your PC: `ping 192.168.68.51` from R58
- Check R58 logs: `./connect-r58-frp.sh 'sudo journalctl -u preke-recorder -f | grep webhook'`

## Ready to Test!

Once DaVinci Resolve is open and the service is running, start a recording session and watch the magic happen! 🎬
