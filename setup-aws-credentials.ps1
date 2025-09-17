# AWS Credentials Setup Script for Windows PowerShell
Write-Host "Setting up AWS credentials for Kubrick..." -ForegroundColor Green

$AWS_ACCESS_KEY_ID = Read-Host "AWS Access Key ID"
$AWS_SECRET_ACCESS_KEY = Read-Host "AWS Secret Access Key" -AsSecureString
$AWS_SECRET_ACCESS_KEY = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($AWS_SECRET_ACCESS_KEY))
$AWS_REGION = Read-Host "AWS Region (default: us-east-1)"
if ([string]::IsNullOrEmpty($AWS_REGION)) { $AWS_REGION = "us-east-1" }

# Update kubrick-api/.env
(Get-Content "kubrick-api/.env") -replace "AWS_ACCESS_KEY_ID=.*", "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID" | Set-Content "kubrick-api/.env"
(Get-Content "kubrick-api/.env") -replace "AWS_SECRET_ACCESS_KEY=.*", "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" | Set-Content "kubrick-api/.env"
(Get-Content "kubrick-api/.env") -replace "AWS_REGION=.*", "AWS_REGION=$AWS_REGION" | Set-Content "kubrick-api/.env"

# Update kubrick-mcp/.env
(Get-Content "kubrick-mcp/.env") -replace "AWS_ACCESS_KEY_ID=.*", "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID" | Set-Content "kubrick-mcp/.env"
(Get-Content "kubrick-mcp/.env") -replace "AWS_SECRET_ACCESS_KEY=.*", "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" | Set-Content "kubrick-mcp/.env"
(Get-Content "kubrick-mcp/.env") -replace "AWS_REGION=.*", "AWS_REGION=$AWS_REGION" | Set-Content "kubrick-mcp/.env"

Write-Host "AWS credentials have been configured!" -ForegroundColor Green
Write-Host "You can now start the services with: docker-compose up" -ForegroundColor Yellow