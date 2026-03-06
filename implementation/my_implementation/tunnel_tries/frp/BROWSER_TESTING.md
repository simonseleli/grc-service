# FIMS FRP Tunnel — Browser Testing Guide

> **Quick Guide:** Access FIMS in browser via FRP tunnel  
> **Time:** ~10 minutes  
> **Date:** 2026-03-02

---

## Prerequisites Checklist

Before you start, verify you have:

- [ ] Docker installed and running
- [ ] FRP server credentials (user: `abc.abc`, token: `abc`, server: `tunnel.ictpack.net:7000`)
- [ ] FIMS code in `/home/simons/Coding/FIMS/`
- [ ] FRP config created (`/home/simons/Coding/FIMS/frp/`)
- [ ] Your computer can access `tunnel.ictpack.net`

---

## Phase 1: Prepare & Start FIMS Services (3-5 minutes)

### Step 1.1: Open Terminal

```bash
cd /home/simons/Coding/FIMS
```

### Step 1.2: Start All FIMS Services

```bash
# Start all Docker services
docker-compose up -d

# Verify services are running
docker-compose ps
```

**Expected output:**

```
SERVICE                              STATUS
fims-iam-service                     Up (healthy)
fims-document-records-service        Up (healthy)
fims-work-orchestration-service      Up (healthy)
fims-client-service                  Up (healthy)
fims-corporate-service               Up (healthy)
fims-api-gateway                     Up (healthy)
staff-portal                         Up
client-portal                        Up
fims-kafka                           Up
fims-zookeeper                       Up
postgres-iam-service                 Up
redis-iam-service                    Up
... (and other databases/caches)
```

### Step 1.3: Wait for Services to Be Healthy

```bash
# Check gateway is ready
curl http://localhost:8080/health

# Expected output:
# healthy
```

**If that doesn't work yet, wait 30 seconds and try again. Services take time to start.**

---

## Phase 2: Start FRP Client (2-3 minutes)

### Step 2.1: Navigate to FRP Directory

```bash
cd /home/simons/Coding/FIMS/frp
```

### Step 2.2: Run FRP Setup Script

```bash
# Run automated setup
./setup-frp.sh setup
```

**This will:**
1. ✓ Check dependencies
2. ✓ Build Docker image
3. ✓ Start FRP client
4. ✓ Verify FRP connection

**Expected output:**

```
[INFO] Building FRP Docker image...
[✓] Docker image built: fims-frp-client:latest
[INFO] Checking Docker network...
[✓] Network exists: fims-network
[INFO] Starting FRP client container...
[✓] Container started: fims-frp-client
[INFO] Waiting for FRP client to connect...
[✓] FRP client successfully connected!
[✓] Container Status: RUNNING
```

### Step 2.3: Verify Connection

```bash
# Watch the logs to confirm connection
docker logs fims-frp-client

# Look for these lines:
# [abc.abc] login success
# proxy name [fims-api-gateway] status [online]
# proxy name [fims-staff-portal] status [online]
# proxy name [fims-client-portal] status [online]
```

✅ **If you see "login success", FRP is connected!**

---

## Phase 3: Test Locally First (1 minute)

### Step 3.1: Test Local Gateway

Before accessing via tunnel, test locally:

```bash
# Test from FRP directory
./test-tunnel.sh local
```

**Expected output:**

```
✓ PASS: Gateway is healthy
✓ PASS: Local tests completed
```

✅ **If local tests pass, gateway is working!**

---

## Phase 4: Access via Browser (Test Time!)

### Step 4.1: Accessing Portals

Now you can access FIMS via FRP tunnel from your browser.

**Open these URLs in your browser:**

#### API Documentation (Swagger/OpenAPI)
```
https://fims-api.tunnel.ictpack.net/api/schema/
```

**Expected:** Interactive API documentation page

---

#### Staff Portal (Internal Staff Interface)
```
https://fcc-staff.tunnel.ictpack.net
```

**Expected:** Login page with fields for email and password

**Test Login:**
- Email: `admin@fcc.go.tz` (or your configured admin email)
- Password: Your admin password
- If MFA is enabled, enter code when prompted

---

#### Client Portal (External Client Interface)
```
https://fcc-client.tunnel.ictpack.net
```

**Expected:** Client portal login page

---

### Step 4.2: Test API Endpoint in Browser (Optional)

Open this in browser (will ask for auth):
```
https://fims-api.tunnel.ictpack.net/api/v1/users/
```

**Expected:** 401 Unauthorized (normal - requires JWT token)

---

## Phase 5: Full Testing (Verify Everything Works)

### Step 5.1: Test All Endpoints

```bash
cd /home/simons/Coding/FIMS/frp

# Run comprehensive tests
./test-tunnel.sh remote
```

**Expected output:**

```
Testing FIMS via FRP Tunnel
✓ API Gateway is accessible via tunnel
✓ CORS headers present
✓ Staff Portal is accessible
✓ Client Portal is accessible
✓ Remote tests completed
```

---

## Troubleshooting While Testing

### Issue 1: Browser Says "Cannot Reach Server"

**Problem:** Tunnel domain not accessible

**Solution:**

```bash
# From your terminal, check if FRP client is running
docker ps | grep frp-client

# Check FRP logs
docker logs fims-frp-client | tail -20

# If not running, restart
docker restart fims-frp-client
sleep 3
docker logs fims-frp-client | grep "login success"
```

### Issue 2: "Connection Refused" or Timeout

**Problem:** FRP not connected to server

**Solution:**

```bash
# Verify FRP credentials in frpc.toml
cat frpc.toml | grep -E "serverAddr|serverPort|user|token"

# Test connectivity to FRP server
telnet tunnel.ictpack.net 7000

# If fails, your network/firewall may block port 7000
```

### Issue 3: Browser Shows "Bad Gateway" (502)

**Problem:** FRP connected but gateway not responding

**Solution:**

```bash
# Check if API Gateway is running
docker ps | grep api-gateway

# If not, restart it
docker-compose restart api-gateway

# Wait 10 seconds
sleep 10

# Check logs
docker logs fims-api-gateway | tail -20
```

### Issue 4: "SSL Certificate Error" in Browser

**Problem:** Browser doesn't trust the certificate

**Solution:**

**Chrome/Edge:**
- Click "Advanced"
- Click "Proceed to [domain]" (at bottom)

**Firefox:**
- Click "Advanced..."
- Click "Accept the Risk and Continue"

**Safari:**
- Will automatically proceed if you confirm

*(This is normal for self-signed certificates)*

### Issue 5: Can't Login to Staff Portal

**Problem:** Login fails or says "Invalid credentials"

**Solution:**

```bash
# Verify there's an admin user in IAM database
docker exec fims-iam-service python manage.py shell

# In Python shell:
from apps.users.models import User
User.objects.filter(email='admin@fcc.go.tz').first()

# If no user, create one:
from apps.users.models import User
User.objects.create_superuser(
    email='admin@fcc.go.tz',
    password='testpass123',
    first_name='Admin',
    last_name='User'
)
```

---

## What to Test in Browser

### Test 1: API Documentation

**URL:** `https://fims-api.tunnel.ictpack.net/api/schema/`

**What to do:**
1. Open URL
2. Look for Swagger UI or ReDoc documentation
3. Try expanding the `/api/v1/auth/login/` endpoint
4. Check if schema loads

**Expected:** Beautiful interactive API docs page

---

### Test 2: Staff Portal Login

**URL:** `https://fcc-staff.tunnel.ictpack.net`

**What to do:**
1. Open URL
2. Enter email: `admin@fcc.go.tz`
3. Enter password: Your admin password
4. Click "Login"

**Expected:** 
- Log in successful → Dashboard appears
- Log in fails → Check admin user exists (see troubleshooting)

---

### Test 3: Client Portal Login

**URL:** `https://fcc-client.tunnel.ictpack.net`

**What to do:**
1. Open URL
2. Enter client email (if client account exists)
3. Enter password
4. Click "Login"

**Expected:** Client dashboard (if client account exists)

---

### Test 4: API Health Check

**URL:** `https://fims-api.tunnel.ictpack.net/health`

**Expected:** 
```
healthy
```

---

## Success Indicators

✅ You've successfully set up FIMS via FRP tunnel when:

- [ ] `docker-compose ps` shows all services running
- [ ] `docker logs fims-frp-client` shows "login success"
- [ ] `./test-tunnel.sh local` passes
- [ ] `./test-tunnel.sh remote` passes
- [ ] Browser can access `https://fims-api.tunnel.ictpack.net/health`
- [ ] Browser can load `https://fcc-staff.tunnel.ictpack.net`
- [ ] Can login to staff portal with admin credentials
- [ ] API calls work with JWT token

---

## Monitoring/Debugging

### Watch All Logs

```bash
# Watch FRP client logs
docker logs -f fims-frp-client

# Watch API Gateway logs (in another terminal)
docker logs -f fims-api-gateway

# Watch IAM service logs (in another terminal)
docker logs -f fims-iam-service
```

### Check Status Anytime

```bash
cd /home/simons/Coding/FIMS/frp
./setup-frp.sh status
```

**Shows:**
- Container running status
- Recent logs
- Access points

### Restart If Needed

```bash
# Restart FRP client
docker restart fims-frp-client

# Restart entire FIMS stack
docker-compose restart

# Restart individual service
docker-compose restart api-gateway
```

---

## Access URLs Reference

| Component | URL | Purpose |
|---|---|---|
| **Health Check** | https://fims-api.tunnel.ictpack.net/health | Verify gateway is up |
| **API Docs** | https://fims-api.tunnel.ictpack.net/api/schema/ | Interactive API documentation |
| **Staff Portal** | https://fcc-staff.tunnel.ictpack.net | Internal staff interface |
| **Client Portal** | https://fcc-client.tunnel.ictpack.net | External client interface |
| **Login API** | https://fims-api.tunnel.ictpack.net/api/v1/auth/login/ | API authentication endpoint |
| **Users API** | https://fims-api.tunnel.ictpack.net/api/v1/users/ | User management API |
| **Documents API** | https://fims-api.tunnel.ictpack.net/api/v1/documents/ | Document management API |

---

## Quick Command Reference

```bash
# Phase 1: Start FIMS
cd /home/simons/Coding/FIMS
docker-compose up -d
docker-compose ps

# Phase 2: Start FRP
cd /home/simons/Coding/FIMS/frp
./setup-frp.sh setup

# Phase 3: Test locally
./test-tunnel.sh local

# Phase 4: Test via tunnel
./test-tunnel.sh remote

# Then: Open browser to https://fcc-staff.tunnel.ictpack.net
```

---

## Diagram: Full Flow

```
Your Browser
    ↓
HTTPS Request to fims-api.tunnel.ictpack.net
    ↓
FRP Server (tunnel.ictpack.net:7000)
    ↓ (TLS Tunnel)
Your Computer
    ↓
FRP Client (Docker)
    ↓
API Gateway (localhost:8080)
    ↓
FIMS Services (internal)
    ├── IAM Service
    ├── Document Records Service
    ├── Work Orchestration Service
    └── ... (all others)
```

---

## Next Steps After Testing

Once you verify it works:

1. ✅ Create test users if needed
2. ✅ Test document upload
3. ✅ Test workflows
4. ✅ Test all endpoints
5. ✅ Share tunnel URL with team if needed
6. ✅ Monitor logs regularly

---

## Need Help?

If something doesn't work:

1. Check logs: `docker logs fims-frp-client`
2. Test locally: `./test-tunnel.sh local`
3. Verify network: `docker network ls`
4. Check credentials: `cat frpc.toml`
5. See TROUBLESHOOTING section above

---

**Status:** Ready to test  
**Last Updated:** 2026-03-02  
**Estimated Time:** 10 minutes

Now go test it! 🚀
