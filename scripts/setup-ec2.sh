#!/bin/bash

# Kubrick AI EC2 Setup Script
# This script configures the environment for EC2 deployment
# Optimized for Amazon Linux 2023

set -e

echo "🚀 Kubrick AI EC2 Setup Script"
echo "================================"
echo "Optimized for Amazon Linux 2023"

# Get EC2 public IP
echo "📡 Getting EC2 public IP..."
EC2_PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "")

if [ -z "$EC2_PUBLIC_IP" ]; then
    echo "⚠️  Could not detect EC2 public IP automatically."
    echo "Please enter your EC2 public IP address:"
    read -r EC2_PUBLIC_IP
fi

echo "✅ Using EC2 Public IP: $EC2_PUBLIC_IP"

# Function to prompt for AWS credentials
setup_aws_credentials() {
    echo ""
    echo "🔐 AWS Credentials Setup"
    echo "========================"
    
    echo "Enter your AWS Access Key ID:"
    read -r AWS_ACCESS_KEY_ID
    
    echo "Enter your AWS Secret Access Key:"
    read -s AWS_SECRET_ACCESS_KEY
    echo ""
    
    echo "Enter your AWS Region (default: us-east-1):"
    read -r AWS_REGION
    AWS_REGION=${AWS_REGION:-us-east-1}
}

# Function to setup MCP server environment
setup_mcp_env() {
    echo ""
    echo "⚙️  Configuring MCP Server..."
    
    cp kubrick-mcp/.env.example kubrick-mcp/.env
    
    # Update AWS credentials
    sed -i "s/AWS_ACCESS_KEY_ID=.*/AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID/" kubrick-mcp/.env
    sed -i "s/AWS_SECRET_ACCESS_KEY=.*/AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY/" kubrick-mcp/.env
    sed -i "s/AWS_REGION=.*/AWS_REGION=$AWS_REGION/" kubrick-mcp/.env
    
    echo "✅ MCP Server environment configured"
}

# Function to setup API server environment
setup_api_env() {
    echo ""
    echo "⚙️  Configuring API Server..."
    
    cp kubrick-api/.env.example kubrick-api/.env
    
    # Update AWS credentials
    sed -i "s/AWS_ACCESS_KEY_ID=.*/AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID/" kubrick-api/.env
    sed -i "s/AWS_SECRET_ACCESS_KEY=.*/AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY/" kubrick-api/.env
    sed -i "s/AWS_REGION=.*/AWS_REGION=$AWS_REGION/" kubrick-api/.env
    
    # Update MCP server URL
    sed -i "s|MCP_SERVER=.*|MCP_SERVER=http://$EC2_PUBLIC_IP:9090/mcp|" kubrick-api/.env
    
    echo "✅ API Server environment configured"
}

# Function to setup production docker-compose
setup_docker_compose() {
    echo ""
    echo "🐳 Configuring Docker Compose for EC2..."
    
    # Copy EC2-optimized compose file
    cp docker-compose.ec2.yml docker-compose.yml
    
    # Update UI environment with EC2 public IP
    sed -i "s/your-ec2-public-ip/$EC2_PUBLIC_IP/g" docker-compose.yml
    
    # Update UI Dockerfile for memory optimization
    sed -i 's|dockerfile: Dockerfile|dockerfile: Dockerfile.ec2|g' docker-compose.yml
    
    echo "✅ Docker Compose configured for EC2 deployment with memory optimization"
}

# Function to test AWS credentials
test_aws_credentials() {
    echo ""
    echo "🧪 Testing AWS credentials..."
    
    # Create temporary AWS credentials file for testing
    mkdir -p ~/.aws
    cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = $AWS_ACCESS_KEY_ID
aws_secret_access_key = $AWS_SECRET_ACCESS_KEY
region = $AWS_REGION
EOF

    # Test AWS CLI if available
    if command -v aws &> /dev/null; then
        if aws bedrock list-foundation-models --region "$AWS_REGION" &> /dev/null; then
            echo "✅ AWS Bedrock access confirmed"
        else
            echo "⚠️  AWS Bedrock access test failed - please check permissions"
        fi
    else
        echo "ℹ️  AWS CLI not installed - skipping credential test"
    fi
}

# Main execution
main() {
    # Check if running on EC2
    if ! curl -s http://169.254.169.254/latest/meta-data/ &> /dev/null; then
        echo "⚠️  This script is designed for EC2 instances"
        echo "You can still use it, but some features may not work correctly"
    fi
    
    # Setup AWS credentials
    setup_aws_credentials
    
    # Setup environment files
    setup_mcp_env
    setup_api_env
    setup_docker_compose
    
    # Test credentials
    test_aws_credentials
    
    echo ""
    echo "🎉 Setup Complete!"
    echo "=================="
    echo ""
    echo "Your Kubrick AI is configured for EC2 deployment:"
    echo "• EC2 Public IP: $EC2_PUBLIC_IP"
    echo "• AWS Region: $AWS_REGION"
    echo "• Memory optimized for EC2 constraints"
    echo ""
    echo "Next steps:"
    echo "1. Build services (may take 10-15 minutes): docker-compose build"
    echo "2. Start the application: docker-compose up -d"
    echo "3. Check logs: docker-compose logs -f"
    echo "4. Access UI: http://$EC2_PUBLIC_IP:3000"
    echo "5. Access API: http://$EC2_PUBLIC_IP:8080"
    echo ""
    echo "⚠️  Note: If build fails with memory errors, try:"
    echo "   • Use t3.medium or larger instance"
    echo "   • Add swap space: sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile"
    echo ""
    echo "For troubleshooting, see: docs/EC2_DEPLOYMENT_GUIDE.md"
}

# Run main function
main "$@"