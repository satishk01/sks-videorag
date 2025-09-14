# EC2 Deployment Guide

This guide provides step-by-step instructions for deploying Kubrick AI on Amazon EC2 with public IP access.

## Prerequisites

- AWS Account with EC2 access
- EC2 instance running Amazon Linux 2 or Ubuntu
- Security groups configured for web access
- Domain name or public IP address

## EC2 Instance Setup

### 1. Launch EC2 Instance

**Recommended Instance Type**: `t3.large` or larger (4GB+ RAM)

**Security Group Rules**:
```
Type            Protocol    Port Range    Source
SSH             TCP         22           Your IP
HTTP            TCP         80           0.0.0.0/0
HTTPS           TCP         443          0.0.0.0/0
Custom TCP      TCP         3000         0.0.0.0/0  (UI)
Custom TCP      TCP         8080         0.0.0.0/0  (API)
Custom TCP      TCP         9090         0.0.0.0/0  (MCP)
```

### 2. Connect to EC2 Instance

```bash
ssh -i your-key.pem ec2-user@your-ec2-public-ip
```

### 3. Install Dependencies

#### For Amazon Linux 2:
```bash
# Update system
sudo yum update -y

# Install Docker
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Git
sudo yum install -y git

# Logout and login again for docker group to take effect
exit
```

#### For Ubuntu:
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io docker-compose git
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ubuntu

# Logout and login again for docker group to take effect
exit
```

## Application Deployment

### 1. Clone Repository

```bash
ssh -i your-key.pem ec2-user@your-ec2-public-ip
git clone https://github.com/multi-modal-ai/multimodal-agents-course.git
cd multimodal-agents-course
```

### 2. Configure Environment Variables

#### Get Your EC2 Public IP
```bash
EC2_PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
echo "Your EC2 Public IP: $EC2_PUBLIC_IP"
```

#### Configure MCP Server
```bash
cp kubrick-mcp/.env.example kubrick-mcp/.env
nano kubrick-mcp/.env
```

Update the following values:
```bash
# AWS Bedrock Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here

# Provider Selection
VISION_PROVIDER=bedrock
EMBEDDINGS_PROVIDER=bedrock

# Server Configuration
MCP_HOST=0.0.0.0
MCP_PORT=9090

# Opik Configuration (optional)
OPIK_API_KEY=your_opik_key_here
OPIK_WORKSPACE=default
OPIK_PROJECT=kubrick-mcp
```

#### Configure API Server
```bash
cp kubrick-api/.env.example kubrick-api/.env
nano kubrick-api/.env
```

Update the following values:
```bash
# AWS Bedrock Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here

# Provider Selection
AGENT_PROVIDER=bedrock

# MCP Server Configuration - REPLACE WITH YOUR EC2 PUBLIC IP
MCP_SERVER=http://YOUR_EC2_PUBLIC_IP:9090/mcp

# Server Configuration
API_HOST=0.0.0.0
API_PORT=8080

# Opik Configuration (optional)
OPIK_API_KEY=your_opik_key_here
OPIK_PROJECT=kubrick-api
```

**Important**: Replace `YOUR_EC2_PUBLIC_IP` with your actual EC2 public IP address.

### 3. Configure UI for Public Access

Update the production docker-compose file:
```bash
cp docker-compose.prod.yml docker-compose.yml
nano docker-compose.yml
```

Replace `your-ec2-public-ip` with your actual EC2 public IP:
```yaml
environment:
  - REACT_APP_API_URL=http://YOUR_EC2_PUBLIC_IP:8080
```

### 4. Deploy Application

```bash
# Build and start services
docker-compose up -d

# Check logs
docker-compose logs -f
```

### 5. Verify Deployment

Check that all services are running:
```bash
docker-compose ps
```

Test endpoints:
```bash
# Test MCP Server
curl http://localhost:9090/health

# Test API Server
curl http://localhost:8080/

# Check from external
curl http://YOUR_EC2_PUBLIC_IP:8080/
```

## Access Your Application

Once deployed, you can access:

- **UI**: `http://YOUR_EC2_PUBLIC_IP:3000`
- **API**: `http://YOUR_EC2_PUBLIC_IP:8080`
- **MCP Server**: `http://YOUR_EC2_PUBLIC_IP:9090`
- **API Docs**: `http://YOUR_EC2_PUBLIC_IP:8080/docs`

## SSL/HTTPS Setup (Optional)

### Using Let's Encrypt with Nginx

1. **Install Nginx**:
```bash
sudo yum install -y nginx  # Amazon Linux
# or
sudo apt install -y nginx  # Ubuntu
```

2. **Configure Nginx**:
```bash
sudo nano /etc/nginx/conf.d/kubrick.conf
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /mcp/ {
        proxy_pass http://localhost:9090/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

3. **Install SSL Certificate**:
```bash
sudo yum install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Monitoring and Maintenance

### 1. View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f kubrick-api
docker-compose logs -f kubrick-mcp
docker-compose logs -f kubrick-ui
```

### 2. Update Application
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

### 3. Backup Data
```bash
# Backup shared media
sudo tar -czf kubrick-backup-$(date +%Y%m%d).tar.gz shared_media/

# Backup environment files
cp kubrick-api/.env kubrick-api/.env.backup
cp kubrick-mcp/.env kubrick-mcp/.env.backup
```

### 4. Monitor Resources
```bash
# Check disk usage
df -h

# Check memory usage
free -h

# Check Docker stats
docker stats
```

## Troubleshooting

### Common Issues

#### 1. Cannot Access from Public IP

**Check Security Groups**:
- Ensure ports 3000, 8080, 9090 are open
- Source should be `0.0.0.0/0` for public access

**Check Services**:
```bash
docker-compose ps
netstat -tlnp | grep -E '(3000|8080|9090)'
```

#### 2. MCP Server Connection Failed

**Check MCP_SERVER URL in API config**:
```bash
grep MCP_SERVER kubrick-api/.env
```

Should be: `MCP_SERVER=http://YOUR_EC2_PUBLIC_IP:9090/mcp`

#### 3. AWS Bedrock Access Denied

**Check AWS Credentials**:
```bash
# Test AWS CLI (install if needed)
aws bedrock list-foundation-models --region us-east-1
```

**Check IAM Permissions**: Ensure your AWS user has Bedrock and Transcribe permissions.

#### 4. Out of Memory

**Increase Instance Size** or **Optimize Docker Resources**:
```yaml
deploy:
  resources:
    limits:
      memory: 2G  # Reduce if needed
```

### Debug Commands

```bash
# Check container logs
docker logs kubrick-api
docker logs kubrick-mcp

# Check container health
docker exec -it kubrick-api curl http://localhost:8080/
docker exec -it kubrick-mcp curl http://localhost:9090/

# Check network connectivity
docker network ls
docker network inspect multimodal-agents-course_agent-network
```

## Performance Optimization

### 1. Instance Optimization

- Use **t3.large** or larger for production
- Enable **detailed monitoring**
- Use **EBS-optimized** instances

### 2. Docker Optimization

```yaml
# In docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      cpus: '1'
      memory: 1G
```

### 3. Application Optimization

- Enable **caching** for API responses
- Use **CDN** for static assets
- Implement **health checks**

## Security Best Practices

1. **Use IAM Roles** instead of access keys when possible
2. **Restrict Security Groups** to necessary IPs
3. **Enable CloudTrail** for API auditing
4. **Use HTTPS** in production
5. **Regular Updates** of system and containers
6. **Monitor Logs** for suspicious activity

## Cost Optimization

1. **Use Spot Instances** for development
2. **Schedule Shutdown** during off-hours
3. **Monitor AWS Costs** with billing alerts
4. **Use Reserved Instances** for production

This guide provides a complete setup for running Kubrick AI on EC2 with public access. The system will be accessible via your EC2 public IP address on the configured ports.