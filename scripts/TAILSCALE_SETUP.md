# Tailscale Setup Guide

This guide helps you set up Tailscale on your server (192.168.1.77) to enable remote access.

## Quick Setup (Automated)

Run the automated setup script:

```bash
cd "/Users/mariusbelstad/R58 app/preke-r58-recorder/scripts"
./setup-tailscale.sh
```

The script will:
1. Install Tailscale on the remote server
2. Start the Tailscale service
3. Guide you through authentication
4. Display the Tailscale IP address

## Manual Setup

If you prefer to set up manually, follow these steps:

### 1. Connect to the Server

```bash
ssh Cursor@192.168.1.77
# Password: vibe1914
```

### 2. Install Tailscale

For Ubuntu/Debian:
```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

For Fedora/RHEL/CentOS:
```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

### 3. Start Tailscale Service

```bash
sudo systemctl enable --now tailscaled
```

### 4. Authenticate

```bash
sudo tailscale up
```

This will display a URL. Open it in your browser and sign in with your Tailscale account.

### 5. Get Your Tailscale IP

```bash
sudo tailscale ip -4
```

## Optional: Configure as Subnet Router

If you want to access other devices on the local network (192.168.1.0/24) via Tailscale:

```bash
# Enable IP forwarding
echo 'net.ipv4.ip_forward = 1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Advertise routes
sudo tailscale up --advertise-routes=192.168.1.0/24 --accept-routes
```

Then approve the routes in your Tailscale admin console:
1. Go to https://login.tailscale.com/admin/machines
2. Find your device
3. Click "..." → "Edit route settings"
4. Enable the 192.168.1.0/24 route

## Accessing the Device

Once set up, you can access the server using its Tailscale IP:

```bash
# Get the Tailscale IP
ssh Cursor@192.168.1.77 "sudo tailscale ip -4"

# Then connect using that IP
ssh Cursor@<tailscale-ip>
```

## Useful Commands

- Check status: `sudo tailscale status`
- View IP: `sudo tailscale ip -4`
- View all devices: `sudo tailscale status --json`
- Disconnect: `sudo tailscale down`
- Reconnect: `sudo tailscale up`

## Troubleshooting

### Cannot connect via SSH
- Ensure the server is online
- Check firewall settings
- Verify SSH service is running: `sudo systemctl status ssh`

### Tailscale not authenticating
- Make sure you have a Tailscale account (sign up at https://tailscale.com)
- Check if the authentication URL is correct
- Try running `sudo tailscale up` again

### Cannot access local network devices
- Ensure subnet routing is configured and approved
- Check that IP forwarding is enabled: `cat /proc/sys/net/ipv4/ip_forward` (should be 1)
