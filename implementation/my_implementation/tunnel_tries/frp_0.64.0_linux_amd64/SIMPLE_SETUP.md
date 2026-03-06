# Use Your Existing FRP Binary — Simpler Solution!

> **Why:** Your FRP binary (0.64.0) already works with TOML config  
> **Problem:** Our Docker image uses older FRP (0.51.0) that only supports INI format  
> **Solution:** Use your existing binary directly!

---

## ✅ Quick Start (30 seconds)

### Option 1: Run in Foreground (Recommended for First Test)

```bash
cd /home/simons/Coding/FIMS/frp_0.64.0_linux_amd64
./run-frpc.sh
```

You'll see:
```
[✓] FRP binary found: /home/simons/Coding/FIMS/frp_0.64.0_linux_amd64/frpc
[✓] Config file found: /home/simons/Coding/FIMS/frp_0.64.0_linux_amd64/frpc.toml
[✓] Starting FRP client...

2026-03-02 08:06:55.488 [I] [sub/root.go:149] start frpc service for config file [frpc.toml]
2026-03-02 08:06:55.488 [I] [client/service.go:319] try to connect to server...
2026-03-02 08:06:56.092 [I] [client/service.go:311] [fb5f0a6787e687ef] login to server success, get run id [fb5f0a6787e687ef]
```

**✓ If you see "login to server success", FRP is connected!**

Press `Ctrl+C` to stop when done testing.

---

### Option 2: Run in Background (For Production)

```bash
cd /home/simons/Coding/FIMS/frp_0.64.0_linux_amd64
./manage-frpc.sh start
```

Then check status anytime:

```bash
./manage-frpc.sh status
```

---

## 🎯 Complete Testing Flow

### Step 1: Start FIMS Services

```bash
cd /home/simons/Coding/FIMS
docker-compose up -d
docker-compose ps
```

### Step 2: Start FRP Tunnel (Foreground)

```bash
cd /home/simons/Coding/FIMS/frp_0.64.0_linux_amd64
./run-frpc.sh
```

**Expected Output:**
```
[✓] login to server success
```

**Keep this terminal open!** (It shows live FRP logs)

### Step 3: Open Another Terminal & Test

In a **new terminal tab/window**:

```bash
cd /home/simons/Coding/FIMS/frp
./test-tunnel.sh remote
```

### Step 4: Open Browser

```
https://fcc-staff.tunnel.ictpack.net
```

---

## 📋 Available Commands

### Direct Execution

```bash
cd /home/simons/Coding/FIMS/frp_0.64.0_linux_amd64

# Run in foreground (see live logs)
./run-frpc.sh

# Check status
./check-status.sh
```

### Background Management

```bash
cd /home/simons/Coding/FIMS/frp_0.64.0_linux_amd64

# Start in background
./manage-frpc.sh start

# Check status
./manage-frpc.sh status

# View logs
./manage-frpc.sh logs

# Stop
./manage-frpc.sh stop

# Restart
./manage-frpc.sh restart
```

---

## 🔄 Recommended Flow

**For Testing:**
```bash
# Terminal 1: FIMS Services
cd /home/simons/Coding/FIMS
docker-compose up -d

# Terminal 2: FRP Client (foreground - see logs)
cd /home/simons/Coding/FIMS/frp_0.64.0_linux_amd64
./run-frpc.sh

# Terminal 3: Testing & Browser
cd /home/simons/Coding/FIMS/frp
./test-tunnel.sh remote
# Then open browser: https://fcc-staff.tunnel.ictpack.net
```

**For Production:**
```bash
# Start FIMS services
cd /home/simons/Coding/FIMS
docker-compose up -d

# Start FRP in background
cd /home/simons/Coding/FIMS/frp_0.64.0_linux_amd64
./manage-frpc.sh start

# Check status
./manage-frpc.sh status

# View logs when needed
./manage-frpc.sh logs
```

---

## 📊 Status Checker

Quick check anytime:

```bash
cd /home/simons/Coding/FIMS/frp_0.64.0_linux_amd64
./check-status.sh
```

Output:
```
✓ FRP Client is RUNNING

Process:
simons  54321  0.0  0.1 123456 7890 ?  Sl  08:07  0:01 /home/simons/Coding/FIMS/frp_0.64.0_linux_amd64/frpc -c /home/simons/Coding/FIMS/frp_0.64.0_linux_amd64/frpc.toml

Configuration:
user = "simon.seleli"
metadatas.token = "i76irkcgdrycdc7o"
serverAddr = "tunnel.ictpack.net"
serverPort = 7000
```

---

## 🛑 Stop Everything

```bash
# Stop FRP
cd /home/simons/Coding/FIMS/frp_0.64.0_linux_amd64
./manage-frpc.sh stop

# Stop FIMS services
cd /home/simons/Coding/FIMS
docker-compose down
```

---

## Why This Works

✓ Your FRP binary (0.64.0) supports TOML config  
✓ Already tested and working with your credentials  
✓ No Docker version conflicts  
✓ Simpler setup - just run a binary  
✓ Easier to debug if issues occur  

---

## 🚀 Next Steps

1. **Start FIMS:** `docker-compose up -d` (main directory)
2. **Start FRP:** `./run-frpc.sh` (frp_0.64.0_linux_amd64 directory)
3. **Test:** `./test-tunnel.sh remote` (frp directory)
4. **Browse:** `https://fcc-staff.tunnel.ictpack.net`

That's it! 🎉

---

## Troubleshooting

### FRP Won't Start

```bash
# Check if FRP binary exists
ls -lh /home/simons/Coding/FIMS/frp_0.64.0_linux_amd64/frpc

# Make sure it's executable
chmod +x /home/simons/Coding/FIMS/frp_0.64.0_linux_amd64/frpc

# Try running directly
./frpc -c frpc.toml
```

### Connection Error

```bash
# Check credentials
grep -E "user|token|serverAddr" frpc.toml

# Test FRP server reachability
telnet tunnel.ictpack.net 7000
```

### Need to Stop Running FRP

```bash
# If running in background
./manage-frpc.sh stop

# If running in foreground
# Press Ctrl+C
```

---

**Status:** Ready to use  
**Method:** Direct binary (simpler & proven to work)  
**Time:** ~5 minutes total setup
