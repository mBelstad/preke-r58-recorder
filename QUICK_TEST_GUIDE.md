# 🚀 VDO.ninja v28 + MediaMTX - Quick Test Guide

**Status:** ✅ All software updated & ready for testing!

---

## ⚡ 30-Second Test

**Just open this URL in your browser:**

```
https://192.168.1.24:8443/?view=cam0&whep=http://192.168.1.24:8889/cam0/whep
```

**Expected:** Video from cam0 appears within 2-3 seconds!

---

## 📋 What Was Done

✅ **MediaMTX:** v1.5.1 → **v1.15.5** (+10 versions!)  
✅ **VDO.ninja:** v25 → **v28.4** (latest stable)  
✅ **Signaling:** Custom → **Simple broadcast** (official)  
✅ **Streams:** 3 cameras active (cam0, cam2, cam3)

---

## 🧪 Test URLs

### Single Camera View (WHEP)
```
https://192.168.1.24:8443/?view=cam0&whep=http://192.168.1.24:8889/cam0/whep
https://192.168.1.24:8443/?view=cam2&whep=http://192.168.1.24:8889/cam2/whep
https://192.168.1.24:8443/?view=cam3&whep=http://192.168.1.24:8889/cam3/whep
```

### Mixer (Multi-Camera)
```
https://192.168.1.24:8443/mixer.html?mediamtx=192.168.1.24:8889
```

### Test Page (All Methods)
```
https://192.168.1.24:8443/test_vdo_v28.html
```

---

## ✅ Success = Video Appears!

**If you see video:**
- ✅ VDO.ninja v28 WHEP integration works!
- ✅ Can use VDO.ninja mixer with MediaMTX
- ✅ Production ready!

---

## ❌ Troubleshooting

**No video?** Check browser console (F12) for errors.

**CORS error?**
```bash
ssh linaro@192.168.1.24
sudo systemctl restart mediamtx
```

**Stream not found?**
```bash
# Verify streams are active
curl http://192.168.1.24:9997/v3/paths/list
```

---

## 📚 Full Documentation

- `FINAL_TEST_SUMMARY.md` - Complete testing guide
- `VDO_NINJA_V28_TEST_RESULTS.md` - Detailed test instructions
- `SOFTWARE_UPDATE_COMPLETE.md` - Update log
- `VDO_NINJA_RESEARCH_FINDINGS.md` - Research results

---

**Ready to test! 🎉**

