#!/bin/bash

# Deployment script for Digital Ocean Droplet
# Run this on your droplet after cloning the repo

#!/bin/bash

# Deployment script for Digital Ocean Droplet
# Run this on your droplet after cloning the repo

# Update system (already done)
# apt update && apt upgrade -y

# Install Docker and Docker Compose (already done)
# apt install -y docker.io docker-compose
# systemctl start docker
# systemctl enable docker

# Set environment variables
export MYSQL_ROOT_PASSWORD=secure_password_123
export SITE_NAME=yourway.uz
export ADMIN_PASSWORD=admin123

# Build and run
docker-compose up -d --build

# Wait for services to start
sleep 30

# Create site (assuming bench is available)
# bench new-site $SITE_NAME --admin-password $ADMIN_PASSWORD --db-root-password $MYSQL_ROOT_PASSWORD

# Install app
# bench --site $SITE_NAME install-app cash_flow_app

# Migrate
# bench --site $SITE_NAME migrate

# Set up nginx for domain (assuming you have domain pointed to droplet IP)
# Edit /etc/nginx/sites-available/default or use certbot for SSL

echo "Deployment complete. Access at http://yourway.uz"