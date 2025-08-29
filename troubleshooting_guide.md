# ReMarkable Backup Troubleshooting Guide

## Current Issue
The backup tool can reach your ReMarkable tablet (ping works, port 22 is open), but SSH connections are being rejected or closed immediately.

## Common Causes and Solutions

### 1. SSH Password Issues
**Problem**: Incorrect SSH password
**Solution**: 
- Double-check the password from Settings → Help → Copyright and licenses → GPLv3 Compliance
- Make sure you're copying the EXACT password (case-sensitive)
- The password changes if you factory reset the tablet

### 2. ReMarkable OS Version
**Problem**: Different ReMarkable OS versions have different SSH configurations
**Solutions**:
- **ReMarkable 1**: SSH should work out of the box
- **ReMarkable 2 (older firmware)**: SSH available immediately
- **ReMarkable 2 (newer firmware)**: May need manual SSH enablement

### 3. SSH Service Not Running
**Problem**: SSH daemon not started or crashed
**Solutions**:
- Restart your ReMarkable tablet (hold power button for 15 seconds, then restart)
- Wait 2-3 minutes after restart before trying to connect
- Try connecting while tablet is at the home screen (not sleeping)

### 4. Network Configuration Issues
**Problem**: USB network interface not properly configured
**Solutions**:
- Try a different USB cable
- Try a different USB port on your computer
- Restart both tablet and computer
- Check Windows network adapters for ReMarkable interface

### 5. Firewall/Antivirus Blocking
**Problem**: Windows firewall or antivirus blocking SSH
**Solutions**:
- Temporarily disable Windows firewall
- Add exception for SSH (port 22) to 10.11.99.1
- Check antivirus settings

## Manual Testing Steps

### Step 1: Verify Basic Connectivity
```bash
ping 10.11.99.1
```
Should reply with `bytes=32 time=1ms TTL=64`

### Step 2: Check Network Interface
```bash
ipconfig
```
Should show an interface with IP `10.11.99.2` (your computer) connecting to ReMarkable's `10.11.99.1`

### Step 3: Test SSH Port
```bash
telnet 10.11.99.1 22
```
Should connect (shows SSH service is listening)

### Step 4: Try SSH with Verbose Output
```bash
ssh -vvv -o ConnectTimeout=10 root@10.11.99.1
```
This will show detailed connection info to help diagnose the issue

## Alternative Solutions

### Option 1: Enable SSH on ReMarkable (if disabled)
Some ReMarkable tablets may have SSH disabled by default:
1. Connect via USB
2. Try accessing the web interface at `http://10.11.99.1`
3. Look for SSH settings or developer mode

### Option 2: Try Different Connection Methods
- **SFTP**: Try connecting with an SFTP client like WinSCP
- **Web Interface**: Check if `http://10.11.99.1` provides file access
- **ReMarkable Cloud**: Use official cloud sync as alternative

### Option 3: Use Third-Party Tools
- **reMarkable Connection Utility**: GUI tool that might handle connection issues better
- **rmapi**: Command-line tool that works with ReMarkable cloud API

## Current Network Status
Based on diagnostics:
- ✅ Tablet is reachable (ping works)
- ✅ USB network interface detected
- ✅ SSH port 22 is open
- ❌ SSH banner exchange fails (connection closed)

This pattern typically indicates either:
1. Wrong SSH password
2. SSH service restarting/unstable
3. Firewall blocking the connection after initial handshake

## Next Steps to Try

1. **Restart ReMarkable tablet** (most common fix)
2. **Wait 2-3 minutes** after restart
3. **Verify password** from tablet settings again
4. **Try the backup tool again**

If none of these work, the tablet may need SSH to be manually enabled or there may be a firmware-specific issue.