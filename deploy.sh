#!/bin/bash

# Deployment script for Digital Ocean Droplet
# Run this on your droplet after cloning the repo

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
sudo apt install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (replace 'user' with your username)
sudo usermod -aG docker $USER

# Clone the repo (if not already)
# git clone https://github.com/Asadtop4ik/cash_flow_app.git
# cd cash_flow_app

# Set environment variables
export MYSQL_ROOT_PASSWORD=secure_password_123
export SITE_NAME=yourway.uz
export ADMIN_PASSWORD=admin123

# Build and run
docker-compose up -d --build

# Wait for services to start
sleep 30

# Create site if not exists
docker-compose exec frappe bench new-site $SITE_NAME --admin-password $ADMIN_PASSWORD --db-root-password $MYSQL_ROOT_PASSWORD

# Install app
docker-compose exec frappe bench --site $SITE_NAME install-app cash_flow_app

# Migrate
docker-compose exec frappe bench --site $SITE_NAME migrate

# Set up nginx for domain (assuming you have domain pointed to droplet IP)
# Edit /etc/nginx/sites-available/default or use certbot for SSL

echo "Deployment complete. Access at http://yourdomain.com"