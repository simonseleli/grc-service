#!/bin/bash

# ============================================
# FIMS FRP Status Check
# ============================================
# Quickly check if FRP client is running

FRP_DIR="/home/simons/Coding/FIMS/frp_0.64.0_linux_amd64"
PROCESS_NAME="frpc"

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "=================================="
echo "  FRP Client Status"
echo "=================================="
echo ""

# Check if running
if pgrep -f "$PROCESS_NAME" > /dev/null; then
    echo -e "${GREEN}✓ FRP Client is RUNNING${NC}"
    echo ""
    echo "Process:"
    ps aux | grep "$PROCESS_NAME" | grep -v grep
    echo ""
else
    echo -e "${RED}✗ FRP Client is NOT running${NC}"
    echo ""
    echo "To start:"
    echo "  cd $FRP_DIR"
    echo "  ./run-frpc.sh"
    echo ""
fi

# Show config
if [ -f "$FRP_DIR/frpc.toml" ]; then
    echo ""
    echo -e "${BLUE}Configuration:${NC}"
    grep -E "user|token|serverAddr|serverPort" "$FRP_DIR/frpc.toml" | head -5
fi

echo ""
