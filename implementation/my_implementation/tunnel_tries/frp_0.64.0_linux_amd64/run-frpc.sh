#!/bin/bash

# ============================================
# FIMS FRP Tunnel — Using Existing Binary
# ============================================
# This script runs FRP client using your existing
# FRP binary (frp_0.64.0_linux_amd64/frpc)
# 
# Your binary already works and supports TOML config!

set -e

FRP_DIR="/home/simons/Coding/FIMS/frp_0.64.0_linux_amd64"
FRP_BINARY="$FRP_DIR/frpc"
CONFIG_FILE="$FRP_DIR/frpc.toml"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# ============================================
# Verify Setup
# ============================================

log_info "Checking FRP binary..."
if [ ! -f "$FRP_BINARY" ]; then
    log_error "FRP binary not found at $FRP_BINARY"
    exit 1
fi
log_success "FRP binary found: $FRP_BINARY"

log_info "Checking configuration file..."
if [ ! -f "$CONFIG_FILE" ]; then
    log_error "Config file not found at $CONFIG_FILE"
    exit 1
fi
log_success "Config file found: $CONFIG_FILE"

# Make binary executable
chmod +x "$FRP_BINARY"

# ============================================
# Show Configuration
# ============================================

log_info "Configuration:"
echo ""
grep -E "user|metadatas.token|serverAddr|serverPort" "$CONFIG_FILE" | head -5
echo ""

# ============================================
# Run FRP Client
# ============================================

log_success "Starting FRP client..."
echo ""

# Run FRP with config
"$FRP_BINARY" -c "$CONFIG_FILE"
