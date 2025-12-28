#!/bin/bash
# Sanitize all hardcoded credentials from documentation
# Replaces sshpass commands with secure SSH key commands

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "======================================"
echo "Credential Sanitization Script"
echo "======================================"
echo ""

FIXED=0
CHECKED=0

# Find all markdown files with sshpass
echo "Scanning for hardcoded credentials..."
echo ""

for file in $(find . -name "*.md" -not -path "./.git/*" -not -path "./node_modules/*"); do
    CHECKED=$((CHECKED + 1))
    
    if grep -q "sshpass -p.*linaro" "$file" 2>/dev/null; then
        echo -e "${YELLOW}Fixing:${NC} $file"
        
        # Create backup
        cp "$file" "$file.bak"
        
        # Replace sshpass commands
        sed -i.tmp 's/sshpass -p '"'"'linaro'"'"' ssh -o StrictHostKeyChecking=no linaro@r58.itagenten.no/ssh linaro@r58.itagenten.no/g' "$file"
        sed -i.tmp 's/sshpass -p "linaro" ssh -o StrictHostKeyChecking=no linaro@r58.itagenten.no/ssh linaro@r58.itagenten.no/g' "$file"
        sed -i.tmp 's/sshpass -p '"'"'linaro'"'"' ssh linaro@r58.itagenten.no/ssh linaro@r58.itagenten.no/g' "$file"
        sed -i.tmp 's/sshpass -p "linaro" ssh linaro@r58.itagenten.no/ssh linaro@r58.itagenten.no/g' "$file"
        sed -i.tmp 's/sshpass -p '"'"'linaro'"'"' scp/scp/g' "$file"
        sed -i.tmp 's/sshpass -p "linaro" scp/scp/g' "$file"
        
        # Remove explicit password mentions
        sed -i.tmp 's/password: `linaro`/use SSH keys - see SECURITY_FIX.md/g' "$file"
        sed -i.tmp 's/(password: `linaro`)/(use SSH keys)/g' "$file"
        sed -i.tmp 's/password: linaro/use SSH keys/g' "$file"
        
        # Clean up temp files
        rm -f "$file.tmp"
        
        FIXED=$((FIXED + 1))
        echo -e "  ${GREEN}✓${NC} Fixed"
    fi
done

echo ""
echo "======================================"
echo "Results"
echo "======================================"
echo ""
echo "Files checked: $CHECKED"
echo -e "Files fixed:   ${GREEN}$FIXED${NC}"
echo ""

if [ $FIXED -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Backup files created (.bak)${NC}"
    echo ""
    echo "To remove backups:"
    echo "  find . -name '*.md.bak' -delete"
    echo ""
    echo "To review changes:"
    echo "  git diff"
    echo ""
fi

echo -e "${GREEN}✓ Sanitization complete!${NC}"
echo ""
echo "IMPORTANT: You must still:"
echo "  1. Change the R58 SSH password"
echo "  2. Set up SSH key authentication"
echo "  3. Test SSH key login works"
echo ""
echo "See SECURITY_FIX.md for complete instructions."
echo ""
