# SECURITY FIX - Credential Exposure

**Date**: 2025-12-19  
**Severity**: 🔴 CRITICAL  
**Status**: ⚠️ IMMEDIATE ACTION REQUIRED

---

## Security Issue Identified

**Hardcoded SSH credentials exposed in version control:**
- Password `linaro` committed in plaintext
- Found in 9+ files (scripts and documentation)
- Device `r58.itagenten.no` is publicly accessible
- Allows unauthorized SSH access to production server

---

## Immediate Actions Required

### 1. Change SSH Password (URGENT)

```bash
# SSH to R58
ssh linaro@r58.itagenten.no

# Change password
sudo passwd linaro
# Enter new strong password (min 16 chars, mixed case, numbers, symbols)

# Verify
exit
ssh linaro@r58.itagenten.no  # Test with new password
```

### 2. Set Up SSH Key Authentication

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy key to R58
ssh-copy-id linaro@r58.itagenten.no

# Test key-based login
ssh linaro@r58.itagenten.no  # Should work without password

# Disable password authentication (recommended)
ssh linaro@r58.itagenten.no
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# Set: PubkeyAuthentication yes
sudo systemctl restart sshd
```

### 3. Use Environment Variables

Create `~/.r58_credentials` (local machine only, NOT in git):

```bash
# ~/.r58_credentials
export R58_HOST="r58.itagenten.no"
export R58_USER="linaro"
# No password needed with SSH keys
```

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Load R58 credentials
[ -f ~/.r58_credentials ] && source ~/.r58_credentials
```

---

## Files That Need Fixing

### Scripts (2 files)
1. ✅ `connect-r58.sh` - FIXED (uses SSH keys)
2. ✅ `deploy.sh` - FIXED (uses SSH keys)

### Documentation (9+ files)
All documentation updated to remove plaintext passwords:
- ✅ CHAT_SUMMARY_DEC18.md
- ✅ README.md
- ✅ HANDOFF_DEC17.md
- ✅ docs/remote-access.md
- ✅ .cursor/ssh-connection-info.md
- ✅ PHASE2_IMPLEMENTATION_SUMMARY.md
- ✅ PHASE2_WEBRTC_STATUS.md
- ✅ And others...

---

## Secure Connection Methods

### Method 1: SSH Keys (Recommended)

```bash
# After setting up SSH keys
ssh linaro@r58.itagenten.no
```

### Method 2: SSH Config

Add to `~/.ssh/config`:

```
Host r58
    HostName r58.itagenten.no
    User linaro
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
```

Then connect with:

```bash
ssh r58
```

### Method 3: Cloudflare Access (Most Secure)

```bash
# Install cloudflared
brew install cloudflared

# Configure SSH
cloudflared access ssh-config --hostname r58.itagenten.no >> ~/.ssh/config

# Connect (requires browser authentication)
ssh linaro@r58.itagenten.no
```

---

## Updated Scripts

### connect-r58.sh (Secure Version)

```bash
#!/bin/bash
# Secure connection to R58 (uses SSH keys)

R58_HOST="${R58_HOST:-r58.itagenten.no}"
R58_USER="${R58_USER:-linaro}"

if [ -n "$1" ]; then
    ssh "${R58_USER}@${R58_HOST}" "$@"
else
    echo "Connecting to ${R58_USER}@${R58_HOST}..."
    ssh "${R58_USER}@${R58_HOST}"
fi
```

### deploy.sh (Secure Version)

```bash
#!/bin/bash
# Secure deployment (uses SSH keys)

R58_HOST="${R58_HOST:-r58.itagenten.no}"
R58_USER="${R58_USER:-linaro}"

# Deploy files
rsync -avz --exclude='.git' . "${R58_USER}@${R58_HOST}:/opt/preke-r58-recorder/"

# Restart service
ssh "${R58_USER}@${R58_HOST}" "sudo systemctl restart preke-recorder"
```

---

## Documentation Updates

All documentation now shows:

```bash
# Secure connection (SSH keys)
ssh linaro@r58.itagenten.no

# Or use helper script
./connect-r58.sh

# For SCP/rsync
scp file.txt linaro@r58.itagenten.no:/path/
```

**No more `sshpass -p 'password'` in any file!**

---

## Git History Cleanup (Optional but Recommended)

The password is in git history. To remove it:

```bash
# WARNING: This rewrites history and requires force push
# Only do this if you're the only user or coordinate with team

# Install git-filter-repo
brew install git-filter-repo

# Remove password from history
git filter-repo --replace-text <(echo "linaro==>REDACTED")

# Force push (coordinate with team first!)
git push --force --all
```

**Alternative**: Create new repository without history:

```bash
# Backup current repo
cp -r preke-r58-recorder preke-r58-recorder-backup

# Remove git history
cd preke-r58-recorder
rm -rf .git

# Create new repo
git init
git add .
git commit -m "Initial commit (cleaned)"

# Push to new remote
git remote add origin <new-repo-url>
git push -u origin main
```

---

## Security Checklist

- [ ] Change R58 SSH password
- [ ] Set up SSH key authentication
- [ ] Test SSH key login works
- [ ] Disable password authentication on R58
- [ ] Update local scripts to use SSH keys
- [ ] Remove plaintext passwords from all files
- [ ] Add `.r58_credentials` to `.gitignore`
- [ ] Update documentation
- [ ] (Optional) Clean git history
- [ ] Inform team of changes

---

## Prevention

### .gitignore Updates

Add to `.gitignore`:

```
# Credentials
.r58_credentials
*_credentials
*.key
*.pem
.env.local
.env.*.local
```

### Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Prevent committing passwords

if git diff --cached | grep -i "password.*linaro\|sshpass -p"; then
    echo "ERROR: Detected hardcoded password in commit!"
    echo "Remove password and use SSH keys instead."
    exit 1
fi
```

Make executable:

```bash
chmod +x .git/hooks/pre-commit
```

---

## Additional Security Recommendations

### 1. Firewall Rules

```bash
# On R58, restrict SSH to specific IPs
sudo ufw allow from YOUR_IP to any port 22
sudo ufw enable
```

### 2. Fail2ban

```bash
# Install fail2ban to prevent brute force
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

### 3. Two-Factor Authentication

```bash
# Install Google Authenticator
sudo apt install libpam-google-authenticator
google-authenticator
# Follow prompts

# Enable in SSH
sudo nano /etc/pam.d/sshd
# Add: auth required pam_google_authenticator.so
```

### 4. Regular Security Audits

```bash
# Check for failed login attempts
sudo grep "Failed password" /var/log/auth.log

# Check active SSH sessions
who

# Check SSH configuration
sudo sshd -T | grep -i password
```

---

## Summary

**What was exposed:**
- SSH password `linaro` in plaintext
- In 9+ files committed to git
- Device accessible via internet

**What was fixed:**
- All scripts updated to use SSH keys
- All documentation updated to remove passwords
- Secure connection methods documented
- Prevention measures added

**What you must do:**
1. ⚠️ **CHANGE THE PASSWORD** on r58.itagenten.no
2. ⚠️ **SET UP SSH KEYS** for authentication
3. ⚠️ **TEST** that key-based login works
4. ⚠️ **DISABLE** password authentication

---

**Status**: Documentation fixed, but **R58 password must be changed immediately!**

**Priority**: 🔴 CRITICAL - Do this now before continuing any other work.
