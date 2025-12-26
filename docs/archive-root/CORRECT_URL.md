# ✅ Correct Switcher URL

## The Correct URL

**Use this URL:** https://recorder.itagenten.no/switcher

~~Not: https://r58.itagenten.no/static/switcher.html~~ ❌

---

## Why the Difference?

The application has a specific route defined in `src/main.py`:

```python
@app.get("/switcher", response_class=HTMLResponse)
async def switcher():
    """Serve the professional switcher interface."""
    switcher_path = Path(__file__).parent / "static" / "switcher.html"
    if switcher_path.exists():
        return switcher_path.read_text()
```

This means:
- The **file** is at: `/opt/preke-r58-recorder/src/static/switcher.html`
- The **URL** is at: `/switcher` (served by FastAPI route)
- The **domain** is: `recorder.itagenten.no` (Cloudflare tunnel)

---

## Verification

✅ WebRTC code is deployed:
```bash
# Verified: WHIPClient library is in the file
grep -c 'WHIPClient' /opt/preke-r58-recorder/src/static/switcher.html
# Result: 1 (found!)
```

✅ Served at correct URL:
```bash
# Verified: WebRTC code is served at /switcher
curl http://localhost:8000/switcher | grep -c 'WHIPClient'
# Result: 1 (found!)
```

---

## Quick Test

1. **Open:** https://recorder.itagenten.no/switcher
2. **Open browser console** (F12)
3. **Look for:** "Attempting WebRTC connection for cam0..."
4. **Expected:** "✓ WebRTC connected for cam0 (compact-input-0)"

---

## All URLs

### Switcher (Phase 2 - WebRTC enabled)
- **Production:** https://recorder.itagenten.no/switcher
- **Local:** http://192.168.1.58:8000/switcher

### Other Interfaces
- **Main (Multiview):** https://recorder.itagenten.no/
- **Graphics:** https://recorder.itagenten.no/static/graphics.html
- **Control:** https://recorder.itagenten.no/static/control.html
- **Library:** https://recorder.itagenten.no/static/library.html

### API
- **Docs:** https://recorder.itagenten.no/docs
- **Mixer Status:** https://recorder.itagenten.no/api/mixer/status
- **Ingest Status:** https://recorder.itagenten.no/api/ingest/status

---

## Ready to Test!

**Open now:** https://recorder.itagenten.no/switcher 🚀

The WebRTC implementation is deployed and ready for testing!



