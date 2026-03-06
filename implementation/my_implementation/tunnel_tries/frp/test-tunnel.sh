#!/bin/bash

# ============================================
# FIMS FRP Tunnel Testing Script
# ============================================
# Tests all FIMS services through FRP tunnel
# Usage: bash test-tunnel.sh [local|remote]

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
TUNNEL_DOMAIN="${TUNNEL_DOMAIN:-tunnel.ictpack.net}"
API_HOST="fims-api.${TUNNEL_DOMAIN}"
STAFF_HOST="fcc-staff.${TUNNEL_DOMAIN}"
CLIENT_HOST="fcc-client.${TUNNEL_DOMAIN}"
LOCAL_HOST="localhost:8080"

# ============================================
# Helper Functions
# ============================================

log_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
}

log_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
}

log_info() {
    echo -e "${BLUE}ℹ INFO${NC}: $1"
}

log_warn() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
}

test_endpoint() {
    local method=$1
    local url=$2
    local expected_status=$3
    local data=$4
    
    log_info "Testing: $method $url"
    
    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" -k "$url" 2>/dev/null || echo "ERROR")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" -k -H "Content-Type: application/json" -d "$data" "$url" 2>/dev/null || echo "ERROR")
    fi
    
    body=$(echo "$response" | head -n -1)
    status=$(echo "$response" | tail -n 1)
    
    if [ "$status" = "$expected_status" ]; then
        log_pass "$url returned $status"
        return 0
    else
        log_fail "$url returned $status (expected $expected_status)"
        return 1
    fi
}

# ============================================
# Local Tests (Using localhost)
# ============================================

test_local() {
    echo ""
    echo "======================================"
    echo "  Testing FIMS Locally (localhost:8080)"
    echo "======================================"
    echo ""
    
    # Health check
    log_info "Testing gateway health..."
    if curl -s -f http://localhost:8080/health > /dev/null 2>&1; then
        log_pass "Gateway is healthy"
    else
        log_fail "Gateway is not responding"
        return 1
    fi
    
    # API gateway
    log_info "Testing API gateway..."
    test_endpoint "GET" "http://localhost:8080/api/v1/auth/login/" 405 || true
    
    # Documents endpoint (without auth should return 401)
    log_info "Testing documents endpoint (expected to require auth)..."
    test_endpoint "GET" "http://localhost:8080/api/v1/documents/" 401 || true
    
    echo ""
    log_pass "Local tests completed"
}

# ============================================
# Remote Tests (Via FRP Tunnel)
# ============================================

test_remote() {
    echo ""
    echo "======================================"
    echo "  Testing FIMS via FRP Tunnel"
    echo "======================================"
    echo "  Domain: $TUNNEL_DOMAIN"
    echo "======================================"
    echo ""
    
    # Check if we can resolve the tunnel domain
    log_info "Checking DNS resolution for $API_HOST..."
    if nslookup "$API_HOST" > /dev/null 2>&1; then
        log_pass "DNS resolves $API_HOST"
    else
        log_warn "DNS resolution failed for $API_HOST (may be normal if tunnel not accessible)"
    fi
    
    echo ""
    
    # Test API Gateway
    log_info "Testing API Gateway via tunnel..."
    if curl -s -k -f "https://$API_HOST/health" > /dev/null 2>&1; then
        log_pass "API Gateway is accessible via tunnel"
    else
        log_fail "API Gateway is not accessible via tunnel"
        log_info "Possible causes:"
        log_info "  1. FRP client not running or not connected"
        log_info "  2. Tunnel domain not configured correctly"
        log_info "  3. FRP server not forwarding requests"
    fi
    
    echo ""
    
    # Test authentication endpoint
    log_info "Testing authentication endpoint..."
    response=$(curl -s -k -X OPTIONS "https://$API_HOST/api/v1/auth/login/" -H "Origin: https://$STAFF_HOST" 2>/dev/null || echo "FAILED")
    
    if echo "$response" | grep -q "Access-Control"; then
        log_pass "CORS headers present"
    else
        log_warn "CORS headers may be missing"
    fi
    
    echo ""
    
    # Test portals accessibility
    log_info "Testing Staff Portal accessibility..."
    if curl -s -k -f "https://$STAFF_HOST" > /dev/null 2>&1; then
        log_pass "Staff Portal is accessible"
    else
        log_warn "Staff Portal not accessible (may need to access via browser)"
    fi
    
    log_info "Testing Client Portal accessibility..."
    if curl -s -k -f "https://$CLIENT_HOST" > /dev/null 2>&1; then
        log_pass "Client Portal is accessible"
    else
        log_warn "Client Portal not accessible (may need to access via browser)"
    fi
    
    echo ""
    log_pass "Remote tests completed"
}

# ============================================
# Detailed Test Suite
# ============================================

test_detailed() {
    local host=$1
    
    echo ""
    echo "======================================"
    echo "  Detailed Tests for $host"
    echo "======================================"
    echo ""
    
    # Test 1: Health endpoint
    log_info "Test 1: Health Check"
    test_endpoint "GET" "https://$host/health" "200" || true
    
    # Test 2: Login endpoint
    log_info "Test 2: Login Endpoint (OPTIONS)"
    test_endpoint "OPTIONS" "https://$host/api/v1/auth/login/" "204" || true
    
    # Test 3: Users list (should require auth)
    log_info "Test 3: Users List (without auth, should fail)"
    test_endpoint "GET" "https://$host/api/v1/users/" "401" || true
    
    # Test 4: Swagger/Schema (usually public)
    log_info "Test 4: API Schema"
    test_endpoint "GET" "https://$host/api/schema/" "200" || true
    
    echo ""
}

# ============================================
# Performance Test
# ============================================

test_performance() {
    local host=$1
    local iterations=10
    
    echo ""
    echo "======================================"
    echo "  Performance Test ($iterations requests)"
    echo "======================================"
    echo ""
    
    log_info "Sending $iterations requests to $host/health..."
    
    total_time=0
    failed=0
    
    for i in $(seq 1 $iterations); do
        echo -n "."
        
        start_time=$(date +%s%N)
        response=$(curl -s -w "%{http_code}" -k "https://$host/health" 2>/dev/null)
        end_time=$(date +%s%N)
        
        status=$(echo "$response" | tail -c 4)
        elapsed=$((($end_time - $start_time) / 1000000)) # Convert nanoseconds to milliseconds
        
        total_time=$(($total_time + $elapsed))
        
        if [ "$status" != "200" ]; then
            ((failed++))
        fi
    done
    
    echo ""
    
    avg_time=$(($total_time / $iterations))
    
    log_pass "Total requests: $iterations"
    log_pass "Failed requests: $failed"
    log_pass "Average response time: ${avg_time}ms"
    
    echo ""
}

# ============================================
# Show Results
# ============================================

show_results() {
    echo ""
    echo "======================================"
    echo "  Test Summary"
    echo "======================================"
    echo ""
    echo "Local Test:        http://localhost:8080"
    echo "Remote Test:       https://$API_HOST"
    echo "Staff Portal:      https://$STAFF_HOST"
    echo "Client Portal:     https://$CLIENT_HOST"
    echo ""
    echo "======================================"
    echo ""
}

# ============================================
# Main
# ============================================

case "${1:-local}" in
    local)
        test_local
        show_results
        ;;
    remote)
        test_remote
        show_results
        ;;
    detailed)
        test_remote
        test_detailed "$API_HOST"
        ;;
    perf|performance)
        test_remote
        test_performance "$API_HOST"
        ;;
    all)
        test_local
        test_remote
        test_detailed "$API_HOST"
        test_performance "$API_HOST"
        show_results
        ;;
    *)
        echo "FIMS FRP Tunnel Test Suite"
        echo ""
        echo "Usage: $0 {local|remote|detailed|perf|all}"
        echo ""
        echo "Options:"
        echo "  local       - Test gateway on localhost:8080"
        echo "  remote      - Test gateway via FRP tunnel"
        echo "  detailed    - Detailed remote tests"
        echo "  perf        - Performance testing via tunnel"
        echo "  all         - Run all tests"
        echo ""
        ;;
esac
