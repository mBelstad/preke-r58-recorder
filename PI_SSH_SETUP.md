# Raspberry Pi SSH Setup

## Current Status

- **SSH Keys**: ✅ Found at `~/.ssh/id_ed25519` and `~/.ssh/id_ed25519.pub`
- **Public Key**: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIL4Jto6hGAhjE3P5g//hyxnXmTotZFKTNNVK2/Z+onGG mariusbelstad@Mariuss-MacBook-Pro.local`
- **Passwordless SSH**: ❌ Not configured (currently using password authentication)
- **Pi IP**: `100.107.248.29` (Tailscale)
- **Pi User**: `marius`
- **Password**: `Famalive94`

## SSH Connection Format

The correct SSH command format is:
```bash
ssh marius@100.107.248.29
```

## Setting Up Passwordless SSH

### Option 1: Use the Setup Script

Run the automated setup script:
```bash
./setup-pi-ssh-key.sh
```

This script will:
1. Check for existing SSH key
2. Copy your public key to the Pi
3. Test passwordless authentication

### Option 2: Manual Setup

1. **Copy your public key to the Pi:**
   ```bash
   ssh-copy-id -i ~/.ssh/id_ed25519.pub marius@100.107.248.29
   ```
   You'll be prompted for the password: `Famalive94`

2. **Test passwordless SSH:**
   ```bash
   ssh marius@100.107.248.29 "echo 'SSH key works!'"
   ```

3. **If it works, you can now connect without password:**
   ```bash
   ssh marius@100.107.248.29
   ```

## Current Scripts

All deployment scripts currently use password authentication via `sshpass`:

- `update-raspberry-pi-pwa.sh` - Updates PWA on Pi
- `clear-pi-pwa-cache.sh` - Clears PWA cache
- `deploy-raspberry-pi-kiosk.sh` - Full kiosk deployment

These scripts will work with password authentication, but after setting up SSH keys, you can modify them to remove `sshpass` for cleaner operation.

## Troubleshooting

### Connection Timeout

If you get "Operation timed out":
1. Check if Pi is online: `ping 100.107.248.29`
2. Check Tailscale status on Pi
3. Verify SSH service is running on Pi: `sudo systemctl status ssh`

### SSH Key Not Working

1. Verify key is on Pi:
   ```bash
   ssh marius@100.107.248.29 "cat ~/.ssh/authorized_keys"
   ```
   Should contain your public key

2. Check permissions on Pi:
   ```bash
   ssh marius@100.107.248.29 "chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
   ```

3. Check SSH config on Pi:
   ```bash
   ssh marius@100.107.248.29 "sudo grep -E 'PubkeyAuthentication|AuthorizedKeysFile' /etc/ssh/sshd_config"
   ```
   Should show:
   - `PubkeyAuthentication yes`
   - `AuthorizedKeysFile .ssh/authorized_keys`

## Next Steps

1. **When Pi is accessible**, run:
   ```bash
   ./setup-pi-ssh-key.sh
   ```

2. **After SSH keys are set up**, you can optionally update scripts to use passwordless SSH:
   - Remove `sshpass -p "$PI_PASSWORD"` from scripts
   - Use direct `ssh` commands instead

3. **Test deployment:**
   ```bash
   ./update-raspberry-pi-pwa.sh
   ```
