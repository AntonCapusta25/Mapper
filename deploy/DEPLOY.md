# NexusScrape $5 Production Deployment Guide

This guide covers how to host your **Autonomous Outreach Factory** on a $5/month Hetzner VPS.

## 1. Recommendations
- **Provider**: Hetzner Cloud
- **Plan**: **CX21** (2 vCPU, 4GB RAM) or **CAX21** (Arm64 equivalent).
- **OS**: Ubuntu 22.04 LTS

## 2. Server Setup (SSH)
Once you have your server's IP address:
```bash
ssh root@your_server_ip
```

## 3. Install Docker
Run these commands on your server:
```bash
# Update and install Docker
apt update && apt install -y docker.io docker-compose
systemctl start docker
systemctl enable docker
```

## 4. Deploy the Application
1. **Transfer the files** (from your local machine):
   ```bash
   # EXCLUDE the database to preserve production data!
   rsync -avz --exclude 'node_modules' --exclude 'venv' --exclude '.git' --exclude '__pycache__' --exclude 'backend/sqlite.db' . root@your_server_ip:/app/
   ```
2. **Setup Environment**:
   ```bash
   cd /app
   cp .env.example .env
   # Edit .env with your Gemini API Key
   nano .env
   ```
3. **Launch**:
   ```bash
   docker-compose up -d --build
   ```

## 5. Access
- **Dashboard**: `http://your_server_ip:3000`
- **Backend API**: `http://your_server_ip:8000`

> [!TIP]
> To enable HTTPS (SSL), you can later add a domain and run `certbot` with an Nginx reverse proxy.
