#!/bin/bash
# Clear PWA cache on Raspberry Pi
# Unregisters service worker and clears browser cache

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
PI_USER="${PI_USER:-marius}"
PI_PASSWORD="${PI_PASSWORD:-Famalive94}"
PI_IP="${PI_IP:-192.168.1.81}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Clearing PWA cache on Raspberry Pi...${NC}"
echo ""

# Check sshpass
if ! command -v sshpass &> /dev/null; then
    echo -e "${RED}Error: sshpass is required${NC}"
    exit 1
fi

# Create a cache-clearing HTML page that will be served temporarily
CACHE_CLEAR_HTML=$(cat <<'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Clearing Cache...</title>
    <script>
        // Unregister all service workers
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.getRegistrations().then(function(registrations) {
                for(let registration of registrations) {
                    registration.unregister().then(function(success) {
                        console.log('Service worker unregistered:', success);
                    });
                }
            });
        }
        
        // Clear all caches
        if ('caches' in window) {
            caches.keys().then(function(names) {
                for (let name of names) {
                    caches.delete(name).then(function(success) {
                        console.log('Cache deleted:', name, success);
                    });
                }
            });
        }
        
        // Clear localStorage and sessionStorage
        localStorage.clear();
        sessionStorage.clear();
        
        // Redirect back after 2 seconds
        setTimeout(function() {
            window.location.href = '/';
        }, 2000);
    </script>
</head>
<body>
    <h1>Clearing PWA cache...</h1>
    <p>Redirecting in 2 seconds...</p>
</body>
</html>
EOF
)

echo -e "${YELLOW}Step 1: Creating temporary cache-clear page...${NC}"
TEMP_FILE=$(mktemp)
echo "$CACHE_CLEAR_HTML" > "$TEMP_FILE"

sshpass -p "$PI_PASSWORD" scp -o StrictHostKeyChecking=no \
    "$TEMP_FILE" \
    "$PI_USER@$PI_IP:/tmp/cache-clear.html"

rm -f "$TEMP_FILE"

echo -e "${GREEN}✓ Cache-clear page created${NC}"
echo ""

echo -e "${YELLOW}Step 2: Temporarily replacing index.html to clear cache...${NC}"
sshpass -p "$PI_PASSWORD" ssh -o StrictHostKeyChecking=no \
    "$PI_USER@$PI_IP" "sudo mv /home/$PI_USER/preke-pwa/index.html /home/$PI_USER/preke-pwa/index.html.backup && \
    sudo cp /tmp/cache-clear.html /home/$PI_USER/preke-pwa/index.html && \
    sudo chown marius:www-data /home/$PI_USER/preke-pwa/index.html && \
    echo 'Cache-clear page installed'"

echo -e "${GREEN}✓ Cache-clear page installed${NC}"
echo ""

echo -e "${YELLOW}Step 3: Restarting nginx...${NC}"
sshpass -p "$PI_PASSWORD" ssh -o StrictHostKeyChecking=no \
    "$PI_USER@$PI_IP" "sudo systemctl restart nginx"

echo -e "${GREEN}✓ Nginx restarted${NC}"
echo ""

echo -e "${YELLOW}Step 4: Waiting 5 seconds for cache to clear...${NC}"
sleep 5

echo -e "${YELLOW}Step 5: Restoring original index.html...${NC}"
sshpass -p "$PI_PASSWORD" ssh -o StrictHostKeyChecking=no \
    "$PI_USER@$PI_IP" "sudo mv /home/$PI_USER/preke-pwa/index.html.backup /home/$PI_USER/preke-pwa/index.html && \
    sudo chown marius:www-data /home/$PI_USER/preke-pwa/index.html && \
    echo 'Original index.html restored'"

echo -e "${GREEN}✓ Original index.html restored${NC}"
echo ""

echo -e "${YELLOW}Step 6: Restarting kiosk service...${NC}"
sshpass -p "$PI_PASSWORD" ssh -o StrictHostKeyChecking=no \
    "$PI_USER@$PI_IP" "sudo systemctl restart preke-kiosk"

echo -e "${GREEN}✓ Kiosk service restarted${NC}"
echo ""

echo -e "${GREEN}======================================"
echo "Cache Cleared!"
echo "======================================"
echo -e "${NC}"
echo "The PWA cache has been cleared on the Raspberry Pi."
echo "The kiosk will reload with fresh code."
echo ""
echo "If videos still don't show, check:"
echo "  1. Browser console for errors (via SSH X11 forwarding)"
echo "  2. WHEP URLs are correct (should use nginx proxy)"
echo "  3. R58 device is reachable from Pi"
echo ""
