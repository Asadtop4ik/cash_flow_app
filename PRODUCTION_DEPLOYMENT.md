# 🚀 Production Deployment Guide - Digital Ocean

**Deployment Method:** Easy Install Script (Official Frappe Method)  
**Platform:** Digital Ocean Droplet ($24/month - 2GB RAM, 2 vCPU, 50GB SSD)  
**Timeline:** 2 kun ichida tayyor bo'lish kerak  
**Domain:** 2 kun ichida beriladi

---

## 📋 Table of Contents

1. [Server Requirements](#server-requirements)
2. [Initial Server Setup](#initial-server-setup)
3. [Easy Install Execution](#easy-install-execution)
4. [Cash Flow App Installation](#cash-flow-app-installation)
5. [Domain & SSL Configuration](#domain--ssl-configuration)
6. [GitHub CI/CD Setup](#github-cicd-setup)
7. [Post-Deployment Checklist](#post-deployment-checklist)
8. [Troubleshooting](#troubleshooting)

---

## 🖥️ Server Requirements

### Digital Ocean Droplet Specs
```
RAM: 2GB minimum (4GB recommended)
CPU: 2 vCPU
Storage: 50GB SSD
OS: Ubuntu 22.04 LTS
```

### Domain Requirements
- DNS A Record: `your-domain.com` → Droplet IP
- DNS A Record: `www.your-domain.com` → Droplet IP
- DNS propagation: 5-15 minutes

---

## 🔧 Initial Server Setup

### Step 1: SSH Connection
```bash
ssh root@YOUR_DROPLET_IP
```

### Step 2: Create Frappe User
```bash
# Add user
sudo adduser frappe --gecos "Frappe User,,,," --disabled-password
echo "frappe:your_secure_password" | sudo chpasswd

# Add to sudo group
sudo usermod -aG sudo frappe

# Configure sudo without password (for deployment)
echo "frappe ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/frappe
```

### Step 3: Switch to Frappe User
```bash
su - frappe
cd ~
```

### Step 4: Update System
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl
```

---

## ⚡ Easy Install Execution

### Single Command Installation (30-40 minutes)

```bash
sudo python3 <(curl -s https://raw.githubusercontent.com/frappe/bench/develop/install.py) \
  --production \
  --user frappe \
  --verbose
```

**Installation Process:**
1. ✅ Install Python 3.10+, Node.js 18, Redis, MariaDB 10.6
2. ✅ Install nginx, supervisor, certbot
3. ✅ Create bench directory: `/home/frappe/frappe-bench`
4. ✅ Install Frappe Framework v15
5. ✅ Create first site (temporary)

**Expected Output:**
```
INFO: Bench frappe-bench initialized
SUCCESS: Frappe installed successfully
INFO: Setting up production...
SUCCESS: Production setup complete
```

### Verify Installation
```bash
cd /home/frappe/frappe-bench
bench --version
# Expected: 5.22.0 or higher

bench version
# Expected: Frappe Framework v15.x.x
```

---

## 📦 Cash Flow App Installation

### Step 1: Get ERPNext (Required Dependency)
```bash
cd /home/frappe/frappe-bench
bench get-app erpnext --branch version-15
```

### Step 2: Get Cash Flow App
```bash
bench get-app https://github.com/YOUR_ORG/cash_flow_app.git
```

### Step 3: Create Production Site with Domain
```bash
# Replace with your actual domain
bench new-site your-domain.com \
  --db-name cashflow_prod \
  --mariadb-root-password YOUR_MARIADB_ROOT_PASSWORD \
  --admin-password YOUR_ADMIN_PASSWORD

# Install apps
bench --site your-domain.com install-app erpnext
bench --site your-domain.com install-app cash_flow_app
```

### Step 4: Remove Default Site (if exists)
```bash
bench use your-domain.com
```

### Step 5: Setup Production Configuration
```bash
# Enable scheduler
bench --site your-domain.com enable-scheduler

# Setup nginx
sudo bench setup production frappe

# Restart services
sudo supervisorctl restart all
```

---

## 🌐 Domain & SSL Configuration

### Step 1: DNS Configuration (Do this BEFORE SSL setup!)

Login to your domain registrar (e.g., Cloudflare, Namecheap) and add:

```
Type: A
Name: @
Value: YOUR_DROPLET_IP
TTL: Auto

Type: A
Name: www
Value: YOUR_DROPLET_IP
TTL: Auto
```

**Wait 5-15 minutes for DNS propagation**, then verify:
```bash
ping your-domain.com
# Should return YOUR_DROPLET_IP
```

### Step 2: Add Domain to Bench
```bash
bench setup add-domain your-domain.com --site your-domain.com
bench setup add-domain www.your-domain.com --site your-domain.com
```

### Step 3: Setup Let's Encrypt SSL
```bash
# Automatic SSL certificate
sudo -H bench setup lets-encrypt your-domain.com \
  --email your-email@example.com

# Setup auto-renewal
sudo bench setup wildcard-ssl your-domain.com \
  --email your-email@example.com
```

### Step 4: Test SSL
```bash
# Visit in browser:
https://your-domain.com
# Should show Frappe login page with green lock icon
```

---

## 🔄 GitHub CI/CD Setup

Your repo already has `.github/workflows/production-deploy.yml` configured! ✅

### Step 1: Generate SSH Key on Server
```bash
# On server as frappe user
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/github_deploy -N ""

# View private key (copy this)
cat ~/.ssh/github_deploy
# Copy entire output including "-----BEGIN/END-----"

# Add public key to authorized_keys
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### Step 2: Configure GitHub Secrets

Go to: `https://github.com/YOUR_ORG/cash_flow_app/settings/secrets/actions`

Add these secrets:

| Secret Name | Value | Example |
|-------------|-------|---------|
| `DROPLET_IP` | Your server IP | `165.227.xxx.xxx` |
| `DROPLET_USER` | `frappe` | `frappe` |
| `SSH_PRIVATE_KEY` | Private key from above | Entire output of `cat ~/.ssh/github_deploy` |

### Step 3: Test CI/CD

Make a test commit:
```bash
# On your local machine
cd /home/asadbek/frappe-bench/apps/cash_flow_app
git checkout main
echo "# Test deployment" >> README.md
git add README.md
git commit -m "test: CI/CD deployment"
git push origin main
```

Watch GitHub Actions: `https://github.com/YOUR_ORG/cash_flow_app/actions`

Expected workflow:
1. ✅ SSH to server
2. ✅ `cd /home/frappe/frappe-bench/apps/cash_flow_app`
3. ✅ `git pull origin main`
4. ✅ `bench migrate --site your-domain.com`
5. ✅ `bench build --app cash_flow_app`
6. ✅ `sudo supervisorctl restart all`

---

## ✅ Post-Deployment Checklist

### 1. Verify Services
```bash
# Check all services running
sudo supervisorctl status

# Expected output:
frappe-bench-redis:frappe-bench-redis-cache       RUNNING
frappe-bench-redis:frappe-bench-redis-queue       RUNNING
frappe-bench-web:frappe-bench-frappe-web          RUNNING
frappe-bench-workers:frappe-bench-frappe-default-worker-0   RUNNING
frappe-bench-workers:frappe-bench-frappe-long-worker-0      RUNNING
frappe-bench-workers:frappe-bench-frappe-short-worker-0     RUNNING
```

### 2. Test Application
```bash
# Access via browser
https://your-domain.com

# Login:
Username: Administrator
Password: YOUR_ADMIN_PASSWORD

# Test:
1. Navigate to Cash Flow module
2. Create test InstApp document
3. Create test Payment Entry
4. Verify supplier debt tracking
```

### 3. Configure Backups
```bash
# Enable automatic backups (daily at 6 AM)
bench --site your-domain.com set-config backup_enabled 1

# Manual backup
bench --site your-domain.com backup --with-files

# List backups
ls ~/frappe-bench/sites/your-domain.com/private/backups/
```

### 4. Setup Monitoring (Optional but Recommended)
```bash
# Install monitoring tools
sudo apt install -y htop iotop

# Check disk usage
df -h

# Check memory
free -m

# Check logs
tail -f ~/frappe-bench/logs/web.error.log
```

---

## 🆘 Troubleshooting

### Issue 1: "Site does not exist"
```bash
bench --site your-domain.com migrate
# If error, check:
ls ~/frappe-bench/sites/
# Your domain folder should exist
```

### Issue 2: 502 Bad Gateway
```bash
# Restart services
sudo supervisorctl restart all

# Check logs
tail -f ~/frappe-bench/logs/web.error.log

# Check nginx config
sudo nginx -t
```

### Issue 3: DNS Not Resolving
```bash
# Wait 15 minutes after DNS changes
ping your-domain.com

# Force DNS refresh
sudo systemd-resolve --flush-caches
```

### Issue 4: SSL Certificate Failed
```bash
# Requirements:
# 1. DNS must be pointing to server (ping test)
# 2. Port 80 and 443 must be open
# 3. No other web server running

# Retry SSL setup
sudo -H bench setup lets-encrypt your-domain.com --email your@email.com
```

### Issue 5: CI/CD Deployment Failed
```bash
# On server, check:
cat ~/.ssh/authorized_keys
# Should contain github_deploy.pub

# Test SSH from local:
ssh -i github_deploy frappe@YOUR_DROPLET_IP "pwd"
# Should output: /home/frappe

# Check GitHub Actions logs for specific error
```

### Issue 6: Payment Entry Not Working
```bash
# Verify custom fields exist
bench --site your-domain.com console

# In Python console:
frappe.get_doc("Custom Field", "Payment Entry-custom_supplier_contract").get("fieldname")
# Should return: custom_supplier_contract

# If not found, run:
bench --site your-domain.com migrate
bench --site your-domain.com clear-cache
```

---

## 📊 Deployment Timeline

### Day 1 (When Server Arrives):
- ⏱️ 1 hour: Initial server setup + Easy Install
- ⏱️ 30 min: Domain DNS configuration (then wait for propagation)
- ⏱️ 20 min: Cash Flow App installation
- ⏱️ 15 min: SSL certificate setup
- ⏱️ 15 min: GitHub CI/CD configuration
- **Total: ~2.5 hours + DNS wait time**

### Day 2:
- ⏱️ 30 min: Testing all features
- ⏱️ 30 min: Backup configuration
- ⏱️ 30 min: Documentation review
- **Total: 1.5 hours**

---

## 📞 Quick Commands Reference

```bash
# Restart all services
sudo supervisorctl restart all

# Update app
cd ~/frappe-bench/apps/cash_flow_app && git pull && cd ~/frappe-bench
bench --site your-domain.com migrate
bench build --app cash_flow_app
sudo supervisorctl restart all

# Backup
bench --site your-domain.com backup --with-files

# Restore backup
bench --site your-domain.com restore ~/frappe-bench/sites/your-domain.com/private/backups/BACKUP_FILE.sql.gz

# Check logs
tail -f ~/frappe-bench/logs/web.error.log
tail -f ~/frappe-bench/logs/worker.error.log

# Enter bench console
bench --site your-domain.com console

# Clear cache
bench --site your-domain.com clear-cache
```

---

## 🎯 Success Criteria

✅ Site accessible via HTTPS  
✅ SSL certificate valid (green lock)  
✅ Login working with Administrator  
✅ Cash Flow module visible  
✅ InstApp document creation working  
✅ Payment Entry with supplier debt tracking working  
✅ CI/CD pipeline deploying automatically on `git push`  
✅ Backups configured and tested  
✅ All supervisor services RUNNING

---

**Ready to deploy in 2 days! 🚀**
