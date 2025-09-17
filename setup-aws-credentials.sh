#!/bin/bash

# AWS Credentials Setup Script
echo "Setting up AWS credentials for Kubrick..."

echo "Please enter your AWS credentials:"
read -p "AWS Access Key ID: " AWS_ACCESS_KEY_ID
read -s -p "AWS Secret Access Key: " AWS_SECRET_ACCESS_KEY
echo
read -p "AWS Region (default: us-east-1): " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}

# Update kubrick-api/.env
sed -i "s/AWS_ACCESS_KEY_ID=.*/AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID/" kubrick-api/.env
sed -i "s/AWS_SECRET_ACCESS_KEY=.*/AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY/" kubrick-api/.env
sed -i "s/AWS_REGION=.*/AWS_REGION=$AWS_REGION/" kubrick-api/.env

# Update kubrick-mcp/.env
sed -i "s/AWS_ACCESS_KEY_ID=.*/AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID/" kubrick-mcp/.env
sed -i "s/AWS_SECRET_ACCESS_KEY=.*/AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY/" kubrick-mcp/.env
sed -i "s/AWS_REGION=.*/AWS_REGION=$AWS_REGION/" kubrick-mcp/.env

echo "AWS credentials have been configured!"
echo "You can now start the services with: docker-compose up"