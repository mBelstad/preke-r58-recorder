# SSH Setup Required

**Status**: ⚠️ ACTION REQUIRED  
**Priority**: HIGH

---

## Current Situation

✅ SSH keys exist on your Mac:
- Private key: `~/.ssh/id_ed25519`
- Public key: `~/.ssh/id_ed25519.pub`

❌ Keys NOT authorized on R58 yet:
- Cannot connect without password
- Scripts will fail until keys are set up

---

## Quick Setup (2 Commands)

### 1. Copy SSH Key to R58

```bash
ssh-copy-id linaro@r58.itagenten.no
```

**Enter password when prompted**: `linaro`

This will:
- Copy your public key to R58
- Add it to `~/.ssh/authorized_keys`
- Enable password-less login

### 2. Test Connection

```bash
ssh linaro@r58.itagenten.no "echo 'SSH keys working!'"
```

Should connect without password prompt.

---

## Your Public Key

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIL4Jto6hGAhjE3P5g//hyxnXmTotZFKTNNVK2/Z+onGG mariusbelstad@Mariuss-MacBook-Pro.local
```

---

## After SSH Keys Are Set Up

### Change R58 Password (CRITICAL)

```bash
ssh linaro@r58.itagenten.no
sudo passwd linaro
# Enter NEW strong password (16+ chars)
exit
```

### Disable Password Authentication (Recommended)

```bash
ssh linaro@r58.itagenten.no
sudo nano /etc/ssh/sshd_config
```

Change these lines:
```
PasswordAuthentication no
PubkeyAuthentication yes
```

Save and restart SSH:
```bash
sudo systemctl restart sshd
exit
```

### Test Scripts Work

```bash
./connect-r58.sh "hostname"
./deploy.sh
```

Both should work without password prompts.

---

## Why This Matters

**Security Issue Fixed**:
- ✅ Removed hardcoded password from 9+ files
- ✅ Updated scripts to use SSH keys
- ✅ Created security documentation

**But**:
- ⚠️ R58 still has default password
- ⚠️ SSH keys not yet authorized
- ⚠️ Password authentication still enabled

**Risk**:
- Anyone with the old password (from git history) can still access R58
- Must change password and use keys

---

## Complete Checklist

- [ ] Copy SSH key: `ssh-copy-id linaro@r58.itagenten.no`
- [ ] Test key login: `ssh linaro@r58.itagenten.no`
- [ ] Change R58 password: `sudo passwd linaro`
- [ ] Disable password auth in `/etc/ssh/sshd_config`
- [ ] Restart SSH: `sudo systemctl restart sshd`
- [ ] Test scripts: `./connect-r58.sh`
- [ ] Verify: `./deploy.sh` (should work without password)

---

## If You Have Issues

### "Permission denied (publickey,password)"

This means SSH keys aren't set up yet. Run:

```bash
ssh-copy-id linaro@r58.itagenten.no
```

### "Host key verification failed"

Remove old host key:

```bash
ssh-keygen -R r58.itagenten.no
```

Then try again.

### "Connection refused"

Check if SSH service is running:

```bash
# Via web interface or another method
sudo systemctl status sshd
```

---

## Summary

**Current Status**:
- ✅ Security fixes committed
- ✅ Scripts updated
- ⚠️ SSH keys need to be authorized
- ⚠️ Password needs to be changed

**Next Steps**:
1. Run: `ssh-copy-id linaro@r58.itagenten.no`
2. Change password
3. Test scripts work

**Time Required**: ~2 minutes

---

**Created**: 2025-12-19  
**Priority**: HIGH - Do this before deploying
