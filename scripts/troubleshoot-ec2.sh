#!/bin/bash

# Kubrick AI EC2 Troubleshooting Script
# This script helps diagnose and fix common EC2 deployment issues

set -e

echo "🔧 Kubrick AI EC2 Troubleshooting"
echo "=================================="

# Function to check system resources
check_resources() {
    echo ""
    echo "📊 System Resources:"
    echo "==================="
    
    echo "Memory Usage:"
    free -h
    
    echo ""
    echo "Disk Usage:"
    df -h
    
    echo ""
    echo "CPU Info:"
    nproc
    
    echo ""
    echo "Swap Status:"
    swapon --show || echo "No swap configured"
}

# Function to check Docker status
check_docker() {
    echo ""
    echo "🐳 Docker Status:"
    echo "================"
    
    if systemctl is-active --quiet docker; then
        echo "✅ Docker service is running"
        echo "Docker version: $(docker --version)"
        echo "Docker Compose version: $(docker-compose --version)"
    else
        echo "❌ Docker service is not running"
        echo "Starting Docker..."
        sudo systemctl start docker
    fi
    
    echo ""
    echo "Docker containers:"
    docker ps -a || echo "No containers found"
    
    echo ""
    echo "Docker images:"
    docker images || echo "No images found"
}

# Function to check network connectivity
check_network() {
    echo ""
    echo "🌐 Network Connectivity:"
    echo "======================="
    
    # Check if we can reach external services
    if curl -s --connect-timeout 5 https://api.github.com > /dev/null; then
        echo "✅ External connectivity OK"
    else
        echo "❌ External connectivity failed"
    fi
    
    # Check EC2 metadata service
    if curl -s --connect-timeout 5 http://169.254.169.254/latest/meta-data/public-ipv4 > /dev/null; then
        echo "✅ EC2 metadata service accessible"
        echo "Public IP: $(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
    else
        echo "❌ EC2 metadata service not accessible"
    fi
    
    # Check ports
    echo ""
    echo "Open ports:"
    netstat -tlnp | grep -E ':(3000|8080|9090)' || echo "No application ports open"
}

# Function to check AWS credentials
check_aws() {
    echo ""
    echo "☁️  AWS Configuration:"
    echo "====================="
    
    if [ -f "kubrick-api/.env" ]; then
        if grep -q "AWS_ACCESS_KEY_ID=" kubrick-api/.env; then
            echo "✅ AWS credentials configured in API"
        else
            echo "❌ AWS credentials missing in API .env"
        fi
    else
        echo "❌ API .env file not found"
    fi
    
    if [ -f "kubrick-mcp/.env" ]; then
        if grep -q "AWS_ACCESS_KEY_ID=" kubrick-mcp/.env; then
            echo "✅ AWS credentials configured in MCP"
        else
            echo "❌ AWS credentials missing in MCP .env"
        fi
    else
        echo "❌ MCP .env file not found"
    fi
    
    # Test AWS CLI if available
    if command -v aws &> /dev/null; then
        echo ""
        echo "Testing AWS Bedrock access..."
        if aws bedrock list-foundation-models --region us-east-1 &> /dev/null; then
            echo "✅ AWS Bedrock access confirmed"
        else
            echo "❌ AWS Bedrock access failed"
        fi
    else
        echo "ℹ️  AWS CLI not installed"
    fi
}

# Function to fix common issues
fix_issues() {
    echo ""
    echo "🔨 Fixing Common Issues:"
    echo "======================="
    
    # Add swap if memory is low
    MEMORY_GB=$(free -g | awk 'NR==2{print $2}')
    if [ "$MEMORY_GB" -lt 4 ]; then
        echo "Low memory detected ($MEMORY_GB GB). Adding swap space..."
        
        if [ ! -f /swapfile ]; then
            sudo fallocate -l 2G /swapfile
            sudo chmod 600 /swapfile
            sudo mkswap /swapfile
            sudo swapon /swapfile
            echo "✅ 2GB swap file created and activated"
        else
            echo "ℹ️  Swap file already exists"
        fi
    fi
    
    # Fix Docker permissions
    if ! groups | grep -q docker; then
        echo "Adding user to docker group..."
        sudo usermod -a -G docker $USER
        echo "⚠️  Please logout and login again for docker group to take effect"
    fi
    
    # Clean up Docker if needed
    DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt 80 ]; then
        echo "High disk usage detected ($DISK_USAGE%). Cleaning up Docker..."
        docker system prune -f
        echo "✅ Docker cleanup completed"
    fi
}

# Function to show service logs
show_logs() {
    echo ""
    echo "📋 Recent Service Logs:"
    echo "======================"
    
    if [ -f "docker-compose.yml" ]; then
        echo "Kubrick MCP logs (last 20 lines):"
        docker-compose logs --tail=20 kubrick-mcp 2>/dev/null || echo "MCP service not running"
        
        echo ""
        echo "Kubrick API logs (last 20 lines):"
        docker-compose logs --tail=20 kubrick-api 2>/dev/null || echo "API service not running"
        
        echo ""
        echo "Kubrick UI logs (last 20 lines):"
        docker-compose logs --tail=20 kubrick-ui 2>/dev/null || echo "UI service not running"
    else
        echo "docker-compose.yml not found"
    fi
}

# Function to test endpoints
test_endpoints() {
    echo ""
    echo "🧪 Testing Endpoints:"
    echo "===================="
    
    EC2_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "localhost")
    
    # Test MCP server
    if curl -s --connect-timeout 5 "http://localhost:9090/" > /dev/null; then
        echo "✅ MCP server responding on localhost:9090"
    else
        echo "❌ MCP server not responding on localhost:9090"
    fi
    
    # Test API server
    if curl -s --connect-timeout 5 "http://localhost:8080/" > /dev/null; then
        echo "✅ API server responding on localhost:8080"
    else
        echo "❌ API server not responding on localhost:8080"
    fi
    
    # Test UI
    if curl -s --connect-timeout 5 "http://localhost:3000/" > /dev/null; then
        echo "✅ UI responding on localhost:3000"
    else
        echo "❌ UI not responding on localhost:3000"
    fi
    
    echo ""
    echo "External access URLs:"
    echo "• UI: http://$EC2_IP:3000"
    echo "• API: http://$EC2_IP:8080"
    echo "• API Docs: http://$EC2_IP:8080/docs"
}

# Main menu
show_menu() {
    echo ""
    echo "Select an option:"
    echo "1. Check system resources"
    echo "2. Check Docker status"
    echo "3. Check network connectivity"
    echo "4. Check AWS configuration"
    echo "5. Fix common issues"
    echo "6. Show service logs"
    echo "7. Test endpoints"
    echo "8. Run all checks"
    echo "9. Exit"
    echo ""
    read -p "Enter your choice (1-9): " choice
}

# Main execution
main() {
    while true; do
        show_menu
        case $choice in
            1) check_resources ;;
            2) check_docker ;;
            3) check_network ;;
            4) check_aws ;;
            5) fix_issues ;;
            6) show_logs ;;
            7) test_endpoints ;;
            8) 
                check_resources
                check_docker
                check_network
                check_aws
                test_endpoints
                ;;
            9) 
                echo "Goodbye!"
                exit 0
                ;;
            *) 
                echo "Invalid option. Please try again."
                ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
    done
}

# Run main function
main "$@"