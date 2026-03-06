#!/bin/bash

# ============================================
# FIMS FRP Tunnel — Background Runner
# ============================================
# Start FRP client in background with supervision
# Logs go to: /tmp/fims-frp.log

set -e

FRP_DIR="/home/simons/Coding/FIMS/frp_0.64.0_linux_amd64"
FRP_BINARY="$FRP_DIR/frpc"
CONFIG_FILE="$FRP_DIR/frpc.toml"
LOG_FILE="/tmp/fims-frp.log"
PID_FILE="/tmp/fims-frp.pid"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
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

# ============================================
# Main Functions
# ============================================

start_frp() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            log_error "FRP client already running (PID: $PID)"
            exit 1
        fi
    fi
    
    log_info "Starting FRP client in background..."
    nohup "$FRP_BINARY" -c "$CONFIG_FILE" > "$LOG_FILE" 2>&1 &
    PID=$!
    echo "$PID" > "$PID_FILE"
    
    sleep 2
    
    # Check if started successfully
    if ps -p "$PID" > /dev/null 2>&1; then
        log_success "FRP client started (PID: $PID)"
        log_info "Logs: tail -f $LOG_FILE"
        echo ""
        sleep 1
        tail -5 "$LOG_FILE"
        echo ""
    else
        log_error "Failed to start FRP client"
        cat "$LOG_FILE"
        exit 1
    fi
}

stop_frp() {
    if [ ! -f "$PID_FILE" ]; then
        log_error "PID file not found - FRP client may not be running"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ps -p "$PID" > /dev/null 2>&1; then
        log_info "Stopping FRP client (PID: $PID)..."
        kill "$PID"
        rm -f "$PID_FILE"
        sleep 1
        log_success "FRP client stopped"
    else
        log_error "PID $PID not found - FRP client may not be running"
        rm -f "$PID_FILE"
        return 1
    fi
}

status_frp() {
    if [ ! -f "$PID_FILE" ]; then
        echo -e "${RED}✗ FRP Client: NOT RUNNING${NC}"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ FRP Client: RUNNING (PID: $PID)${NC}"
        echo ""
        echo "Recent logs:"
        tail -10 "$LOG_FILE"
        return 0
    else
        echo -e "${RED}✗ FRP Client: NOT RUNNING${NC}"
        echo ""
        echo "Last logs:"
        tail -10 "$LOG_FILE"
        return 1
    fi
}

logs_frp() {
    if [ ! -f "$LOG_FILE" ]; then
        log_error "Log file not found"
        exit 1
    fi
    
    log_info "Tailing logs (Ctrl+C to exit)..."
    tail -f "$LOG_FILE"
}

# ============================================
# Main
# ============================================

case "${1:-status}" in
    start)
        start_frp
        ;;
    stop)
        stop_frp
        ;;
    restart)
        stop_frp 2>/dev/null || true
        sleep 1
        start_frp
        ;;
    status)
        status_frp
        ;;
    logs)
        logs_frp
        ;;
    *)
        echo "FIMS FRP Tunnel - Background Manager"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Examples:"
        echo "  $0 start       # Start FRP in background"
        echo "  $0 stop        # Stop FRP client"
        echo "  $0 restart     # Restart FRP client"
        echo "  $0 status      # Show status and recent logs"
        echo "  $0 logs        # Tail logs (Ctrl+C to exit)"
        echo ""
        ;;
esac
